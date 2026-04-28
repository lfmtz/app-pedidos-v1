import os
import json
import gspread
import streamlit as st
from google.oauth2.service_account import Credentials


def get_client():
    creds_json = os.environ.get("GOOGLE_CREDENTIALS")
    if not creds_json:
        try:
            with open("credenciales.json") as f:
                creds_json = f.read()
        except FileNotFoundError:
            st.error("❌ No se encontró el archivo 'credenciales.json'.")
            st.stop()

    creds_dict = json.loads(creds_json)
    scopes = ["https://www.googleapis.com/auth/spreadsheets",
              "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    return gspread.authorize(creds)


def buscar_cliente_por_rfc(rfc):
    client = get_client()
    sheet = client.open("SOL_CREDITO_ACTUAL_2026").sheet1
    registros = sheet.get_all_records()
    for row in registros:
        if str(row.get('RFC', '')).strip().upper() == rfc.strip().upper():
            return row
    return None


def guardar_pedido_y_actualizar_t2(datos, id_actualizar=None):
    client = get_client()
    doc_pedido = client.open("FORMATO DE PEDIDO_26")
    sheet_pedido = doc_pedido.worksheet("datos_pedidos")
    sheet_formato = doc_pedido.worksheet("Pedido")

    # --- 1. DETERMINAR ID Y FILA ---
    todas_las_filas = sheet_pedido.get_all_values()

    if id_actualizar:
        # Modo Edición: Buscar en qué fila está el ID (asumiendo que el ID está en la Columna A / índice 0)
        id_seguimiento = id_actualizar
        fila_destino = -1
        for i, fila in enumerate(todas_las_filas):
            if fila[0] == id_actualizar:
                fila_destino = i + 1  # +1 porque Google Sheets empieza en 1
                break

        # Si por alguna razón no lo encuentra, hacemos un append al final
        if fila_destino == -1:
            fila_destino = len(todas_las_filas) + 1
    else:
        # Modo Nuevo: Generar ID nuevo
        id_seguimiento = f"PED-{len(todas_las_filas) + 1:03d}"
        fila_destino = len(todas_las_filas) + 1

    # --- 2. MAPEO (Columnas 1 a 46) ---
    # Asegúrate de que los nombres coincidan EXACTAMENTE con las llaves en app.py
    mapeo = {
        "ID_Seguimiento": 1, "Nombre (s):": 2, "Primer Apellido:": 3, "Segundo Apellido:": 4,
        "RFC:": 5, "CURP:": 6, "Nombre de Vialidad:": 7, "Tipo de Vialidad:": 8,
        "Número Exterior:": 9, "Número Interior:": 10, "Nombre de la Colonia:": 11,
        "Nombre de la Localidad:": 12, "Nombre del Municipio o Demarcación Territorial:": 13,
        "Nombre de la Entidad Federativa:": 14, "Código Postal:": 15,
        "Correo Electrónico": 16, "Número Celular": 17, "Identificaciones": 18,
        "EMISION": 19, "FOLIO": 20, "Auto": 21, "Precio Auto": 22,
        "Color": 23, "Pago Inicial": 24, "Plazo": 25, "Mensualidades": 26,
        "Monto a Financiar": 27, "AÑO": 28, "OCUPACION": 29,
        "FINANCIER PROPIA": 30, "CONTADO": 31, "BANCARIO": 32, "KUNA": 33,
        "SICREA": 34, "OTRO": 35,
        "GARANTIA EXTENDIDA": 36, "SEGURO": 37, "KIT DE SEGURIDAD": 38,
        "GESTORIA": 39, "PLACAS / TENENCIA": 40, "VERIFICACION": 41,
        "ACCESORIOS": 42, "TOMA DE AUTO": 43, "PRECIO DE TOMA": 44,
        "GERENTE DE AUTOS SEMINUEVOS": 45, "GERENTE DE VENTAS": 46,
        "USO_CFDI": 47, "MET_PAGO": 48, "ANTICIPO": 49
    }

    fila_a_inyectar = [""] * 49
    datos["ID_Seguimiento"] = id_seguimiento  # Corregido NameError

    for campo, valor in datos.items():
        if campo in mapeo:
            columna_idx = mapeo[campo] - 1
            fila_a_inyectar[columna_idx] = str(valor).upper() if valor else ""

        # Refuerzo para Vialidad (por si acaso)
        elif "Vialidad" in campo or "Calle" in campo:
            if fila_a_inyectar[6] == "":
                fila_a_inyectar[6] = str(valor).upper()

    # --- 3. GUARDADO EN HOJA DE DATOS ---
    try:
        if id_actualizar and fila_destino <= len(todas_las_filas):
            # ACTUALIZAR fila existente
            # Cambiamos AT (46) por AW (49) para que incluya los nuevos campos
            rango_update = f"A{fila_destino}:AW{fila_destino}"
            sheet_pedido.update(rango_update, [fila_a_inyectar])
        else:
            # INSERTAR fila nueva
            sheet_pedido.append_row(fila_a_inyectar)
    except Exception as e:
        import streamlit as st
        st.error(f"Error al guardar datos: {e}")

    # --- 4. ACTUALIZACIÓN CELDA T2 (Para impresión) ---
    try:
        sheet_formato.update(values=[[id_seguimiento]], range_name='T2')
    except:
        sheet_formato.update('T2', [[id_seguimiento]])

    return id_seguimiento


def inyectar_t2_existente(id_seguimiento):
    client = get_client()
    doc_pedido = client.open("FORMATO DE PEDIDO_26")
    sheet_formato = doc_pedido.worksheet("Pedido")
    try:
        sheet_formato.update(values=[[id_seguimiento]], range_name='T2')
    except:
        sheet_formato.update('T2', [[id_seguimiento]])


def buscar_contacto_externo(rfc_busqueda):
    try:
        client = get_client()
        sheet_base = client.open("SOL_CREDITO_ACTUAL_2026").sheet1
        celda = sheet_base.find(rfc_busqueda.strip().upper())
        fila_valores = sheet_base.row_values(celda.row)
        celular = fila_valores[12] if len(fila_valores) > 12 else ""
        correo = fila_valores[13] if len(fila_valores) > 13 else ""
        return correo, celular
    except:
        return "", ""

# Agrega esta función al final de tu archivo modulos/sheets_db.py


def obtener_datos_pedido_por_id(id_seguimiento):
    """Busca un pedido por ID y devuelve un diccionario con sus valores."""
    try:
        client = get_client()
        sheet_pedido = client.open(
            "FORMATO DE PEDIDO_26").worksheet("datos_pedidos")

        # Buscamos el ID en la columna A (columna 1)
        celda = sheet_pedido.find(id_seguimiento.strip().upper())
        if not celda:
            return None

        # Obtenemos todos los valores de esa fila
        valores_fila = sheet_pedido.row_values(celda.row)

        # Definimos los encabezados tal cual los tienes en el Excel
        encabezados = [
            "ID_Seguimiento", "Nombre (s):", "Primer Apellido:", "Segundo Apellido:", "RFC:", "CURP:",
            "Nombre de Vialidad:", "Tipo de Vialidad:", "Número Exterior:", "Número Interior:",
            "Nombre de la Colonia:", "Nombre de la Localidad:", "Nombre del Municipio o Demarcación Territorial:",
            "Nombre de la Entidad Federativa:", "Código Postal:", "Correo Electrónico", "Número Celular",
            "Identificaciones", "EMISION", "FOLIO", "Auto", "Precio Auto", "Color", "Pago Inicial",
            "Plazo", "Mensualidades", "Monto a Financiar", "AÑO", "OCUPACION", "FINANCIERA PROPIA",
            "CONTADO", "BANCARIO", "KUNA", "OTRO", "SICREA", "GARANTIA EXTENDIDA", "SEGURO",
            "KIT DE SEGURIDAD", "GESTORIA", "PLACAS / TENENCIA", "VERIFICACION", "ACCESORIOS",
            "TOMA DE AUTO", "PRECIO DE TOMA", "GERENTE DE AUTOS SEMINUEVOS", "GERENTE DE VENTAS",
            "USO_CFDI", "MET_PAGO", "ANTICIPO"
        ]

        # Creamos el diccionario emparejando encabezado con valor
        datos_pedido = {}
        for i, encabezado in enumerate(encabezados):
            if i < len(valores_fila):
                datos_pedido[encabezado] = valores_fila[i]
            else:
                datos_pedido[encabezado] = ""

        return datos_pedido
    except Exception as e:
        st.error(f"Error al recuperar el pedido: {e}")
        return None


def obtener_url_impresion(pestana):
    """
    Configuración de impresión ajustada con los GIDs reales 
    sacados de los enlaces proporcionados.
    """
    spreadsheet_id = "1XxB_Sd7yM_B8Wg4PpbraDtR1VBYmcZmKZjHhWM_2qxA"

    # GIDs ACTUALIZADOS SEGÚN TUS LINKS:
    # Stellantis: 1351176481
    # Pedido Nissan: 211566386
    gids = {
        "Pedido": "211566386",
        "pedido_stellantis": "1351176481"
    }

    gid = gids.get(pestana, "211566386")

    # URL de exportación limpia para PDF
    url = (
        f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/export?"
        f"format=pdf&gid={gid}"
        "&size=letter"              # Tamaño Carta
        "&portrait=true"            # Vertical
        "&fitw=true"                # Ajustar al ancho de página
        "&gridlines=false"          # Sin líneas de cuadrícula
        "&printtitle=false"         # Sin título del documento
        "&sheetnames=false"         # Sin nombre de la hoja
        "&fzr=false"                # Sin repetir filas congeladas
        # --- ESTO ES LO QUE ARREGLA LOS MÁRGENES ---
        "&top_margin=0.50"          # Margen superior
        "&bottom_margin=0.50"       # Margen inferior
        "&left_margin=0.50"         # Margen izquierdo
        "&right_margin=0.50"        # Margen derecho
    )
    return url


def obtener_url_pld(parte):
    """
    Genera el link de impresión individual para las 3 partes del PLD.
    """
    spreadsheet_id = "1XxB_Sd7yM_B8Wg4PpbraDtR1VBYmcZmKZjHhWM_2qxA"

    # GIDs que me pasaste para cada parte
    gids = {
        "PLD_1": "117614662",
        "PLD_2": "486590056",
        "PLD_3": "1210346388"
    }

    gid = gids.get(parte)

    url = (
        f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/export?"
        f"format=pdf&gid={gid}"
        "&size=letter"
        "&portrait=true"
        "&fitw=true"
        "&gridlines=false"
        "&printtitle=false"
        "&sheetnames=false"
        "&fzr=false"
        # --- ESTO ES LO QUE ARREGLA LOS MÁRGENES ---
        "&top_margin=0.20"      # Margen superior
        "&bottom_margin=0.20"   # Margen inferior
        "&left_margin=0.20"     # Margen izquierdo
        "&right_margin=0.20"    # Margen derecho
    )
    return url


def inyectar_datos_generico(datos, nombre_hoja):
    try:
        client = get_client()
        doc = client.open("FORMATO DE PEDIDO_26")
        sheet = doc.worksheet(nombre_hoja)

        cabeceros = sheet.row_values(1)
        nueva_fila = [""] * len(cabeceros)

        for i, nombre_columna in enumerate(cabeceros):
            # Ahora buscará ID_Seguimiento, RFC:, etc.
            if nombre_columna in datos:
                valor = datos[nombre_columna]
                nueva_fila[i] = str(valor).upper() if valor else ""

        sheet.append_row(nueva_fila)
        return True
    except Exception as e:
        import streamlit as st
        st.error(f"Error en {nombre_hoja}: {e}")
        return False
