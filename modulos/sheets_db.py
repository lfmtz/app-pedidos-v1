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


def obtener_url_impresion(hoja_nombre):
    """Genera la URL para descargar el PDF del rango específico de la hoja."""
    # ID del documento (lo sacas de la URL de tu navegador en Google Sheets)
    # Pon aquí el ID largo de tu archivo FORMATO DE PEDIDO_26
    spreadsheet_id = "1XxB_Sd7yM_B8Wg4PpbraDtR1VBYmcZmKZjHhWM_2qxA"

    # GIDs de las hojas (debes buscarlos en la URL de cada pestaña: gid=XXXX)
    gids = {
        "Pedido": "211566386",  # Cambia por el GID real de la hoja Pedido
        "pedido_stellantis": "1351176481"  # Cambia por el GID real de pedido_stellantis
    }

    gid = gids.get(hoja_nombre, "0")
    rango = "A1:S85" if hoja_nombre == "Pedido" else "A1:S74"

    # URL de exportación PDF con parámetros de formato profesional
    url = (
        f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/export?"
        f"format=pdf&gid={gid}&range={rango}"
        "&size=letter"          # Tamaño Carta
        "&portrait=true"        # Orientación Vertical
        "&fitw=true"            # Ajustar al ancho de la página
        "&gridlines=false"      # Ocultar líneas de división
        "&printtitle=false"     # No imprimir nombre del archivo
        "&sheetnames=false"     # No imprimir nombre de la pestaña
        "&fzr=false"            # Evitar repetir filas inmovilizadas
    )
    return url


def obtener_url_pld_completo():
    """Genera un PDF uniendo rangos específicos de las 3 pestañas de PLD."""
    spreadsheet_id = "1XxB_Sd7yM_B8Wg4PpbraDtR1VBYmcZmKZjHhWM_2qxA"

    # GIDs de tus pestañas
    gid1 = "117614662"   # PLD_1
    gid2 = "486590056"   # PLD_2
    gid3 = "1210346388"  # PLD_3

    # Definimos los rangos para que se vea como en tu imagen
    # Si PLD_2 y PLD_3 tienen tamaños similares, A1:I37 funcionará perfecto.
    rango1 = "A1:I37"
    rango2 = "A1:I37"
    rango3 = "A1:I37"

    url = (
        f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/export?"
        f"format=pdf"
        f"&size=letter"          # Tamaño Carta
        f"&portrait=true"        # Vertical
        f"&scale=4"              # <--- ESCALA "Ajustar a la página"
        f"&top_margin=0.5"       # Márgenes pequeños para que luzca el formato
        f"&bottom_margin=0.5"
        f"&left_margin=0.5"
        f"&right_margin=0.5"
        f"&gridlines=false"
        f"&printtitle=false"
        f"&sheetnames=false"
        f"&fzr=false"
        f"&gid={gid1}"           # Hoja inicial
        f"&range={rango1}"       # Rango de la primera hoja
        f"&select={gid1},{gid2},{gid3}"  # Une las tres
    )
    return url
