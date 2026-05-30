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
        "USO_CFDI": 47, "MET_PAGO": 48, "ANTICIPO": 49,
        "Fecha_nac": 50  # Columna AX
    }

    fila_a_inyectar = [""] * 50
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
            rango_update = f"A{fila_destino}:AX{fila_destino}"
            sheet_pedido.update(rango_update, [fila_a_inyectar])
        else:
            sheet_pedido.append_row(fila_a_inyectar)

        # --- 4. ACTUALIZACIÓN CELDA T2 ---
        try:
            sheet_formato.update(values=[[id_seguimiento]], range_name='T2')
        except:
            sheet_formato.update('T2', [[id_seguimiento]])

        return id_seguimiento  # <--- CRÍTICO: Debe estar fuera de los mini-try internos

    except Exception as e:
        import streamlit as st
        st.error(f"❌ Error al guardar datos: {e}")
        return None  # Si falla, devuelve None para que app.py sepa que hubo error

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


@st.cache_data(ttl=120)
def obtener_listado_clientes():
    """Devuelve un listado resumido de clientes (ID, Nombre, Apellido) de datos_pedidos."""
    try:
        client = get_client()
        sheet = client.open("FORMATO DE PEDIDO_26").worksheet("datos_pedidos")
        registros = sheet.get_all_records()
        listado = []
        for row in registros:
            id_seg = str(row.get("ID_Seguimiento", "")).strip()
            if id_seg:
                listado.append({
                    "ID_Seguimiento": id_seg,
                    "Nombre (s):": str(row.get("Nombre (s):", "")).strip(),
                    "Primer Apellido:": str(row.get("Primer Apellido:", "")).strip(),
                    "RFC:": str(row.get("RFC:", "")).strip(),
                })
        return listado
    except Exception as e:
        st.error(f"Error al cargar listado de clientes: {e}")
        return []


def eliminar_registro_por_id(id_seguimiento, nombre_hoja="datos_pedidos"):
    """Elimina la fila cuyo ID_Seguimiento coincida en la hoja indicada."""
    try:
        client = get_client()
        sheet = client.open("FORMATO DE PEDIDO_26").worksheet(nombre_hoja)
        celda = sheet.find(id_seguimiento.strip().upper())
        if celda:
            sheet.delete_rows(celda.row)
            return True
        return False
    except Exception as e:
        st.error(f"❌ Error al eliminar registro: {e}")
        return False


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
        "pedido_stellantis": "1351176481",
        "pedido_stellantis_pm": "92238292",
        "pedido_pm_nissan": "1414537373"
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
        "PLD_3": "1210346388",
        "PLD_1_RL": "568290328",   # <--- GID Nissan
        "PLD_2_RL": "27081065",    # <--- GID Nissan
        "PLD_3_RL": "3155416",     # <--- GID Nissan
        "PLD_PM1": "1399473913",   # <--- GID Nissan
        "PLD_PM2": "958456137",    # <--- GID Nissan
        "PLD_PM3": "1201767317",    # <--- GID Nissan
        "PF_STELLANTIS_1": "794707996",      # Stellantis Persona Física Parte 1
        "PF_STELLANTIS_2": "1196692696",     # Stellantis Persona Física Parte 2
        "PF_STELLANTIS_RL_1": "1023130744",  # Stellantis Representante Legal Parte 1
        "PF_STELLANTIS_RL_2": "885241452",   # Stellantis Representante Legal Parte 2
        "PM_STELLANTIS_1": "1148369144",     # Stellantis Persona Moral Parte 1
        "PM_STELLANTIS_2": "1897580362"      # Stellantis Persona Moral Parte 2
    }

    gid = gids.get(parte, "117614662")

    url = (
        f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/export?"
        f"format=pdf&gid={gid}"
        "&size=letter"
        "&portrait=true"
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

    if parte == "PF_STELLANTIS_1":
        # Escalar a una sola hoja y establecer rango A1:P94
        url += "&scale=4&range=A1%3AP94"
    else:
        # Por defecto, ajustar al ancho
        url += "&fitw=true"

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


def actualizar_ultimo_registro_hoja(nombre_hoja, id_seguimiento):
    """Actualiza la celda T2 de la hoja especificada."""
    try:
        client = get_client()
        doc = client.open("FORMATO DE PEDIDO_26")
        hoja = doc.worksheet(nombre_hoja)
        hoja.update_acell('T2', id_seguimiento)
        return True
    except Exception as e:
        import streamlit as st
        st.error(f"❌ Error en puntero T2 ({nombre_hoja}): {e}")
        return False


def actualizar_campo_pld_representante(id_seguimiento):
    """Actualiza la celda H1 de la hoja PLD_1_RL."""
    try:
        client = get_client()
        doc = client.open("FORMATO DE PEDIDO_26")
        hoja_pld = doc.worksheet("PLD_1_RL")
        hoja_pld.update_acell('H1', id_seguimiento)
        return True
    except Exception as e:
        import streamlit as st
        st.error(f"❌ Error en puntero H1 (PLD_1_RL): {e}")
        return False


def generar_id_especifico(nombre_hoja, prefijo):
    """
    Cuenta los registros en una hoja específica y genera un nuevo ID.
    Ejemplo: PM-005, RL-010
    """
    try:
        client = get_client()
        sheet = client.open("FORMATO DE PEDIDO_26").worksheet(nombre_hoja)
        # Contamos cuántas filas hay (menos el encabezado)
        total_filas = len(sheet.get_all_values())
        nuevo_id = f"{prefijo}-{total_filas:03d}"
        return nuevo_id
    except Exception as e:
        print(f"Error al generar ID para {nombre_hoja}: {e}")
        return f"{prefijo}-ERR"

@st.cache_data(ttl=300)
def obtener_representantes_legales():
    """Obtiene una lista de representantes legales desde la hoja REPRESENTANTE_LEGAL."""
    try:
        client = get_client()
        sheet = client.open("FORMATO DE PEDIDO_26").worksheet("REPRESENTANTE_LEGAL")
        registros = sheet.get_all_records()
        return registros
    except Exception as e:
        import streamlit as st
        st.error(f"Error al obtener representantes: {e}")
        return []

def actualizar_representante_en_pm_stellantis(id_representante):
    """Actualiza la celda O3 de la hoja PM_STELLANTIS_1."""
    try:
        client = get_client()
        doc = client.open("FORMATO DE PEDIDO_26")
        hoja = doc.worksheet("PM_STELLANTIS_1")
        hoja.update_acell('O3', id_representante)
        return True
    except Exception as e:
        import streamlit as st
        st.error(f"❌ Error al actualizar representante en PM_STELLANTIS_1: {e}")
        return False

@st.cache_data(ttl=3600)
def obtener_catalogo_ocupaciones(hoja_catalogo):
    """Obtiene la lista de ocupaciones de ACT_PM o ACT_PF."""
    try:
        client = get_client()
        # Intentamos abrir en el formato de pedido
        try:
            sheet = client.open("FORMATO DE PEDIDO_26").worksheet(hoja_catalogo)
        except:
            # Fallback en caso de que esté en el otro archivo
            sheet = client.open("SOL_CREDITO_ACTUAL_2026").worksheet(hoja_catalogo)
            
        registros = sheet.get_all_records()
        col_name = "ACT_ECON_PM" if hoja_catalogo == "ACT_PM" else "ACT_ECON_PF"
        
        lista = ["SELECCIONE UNA OPCIÓN"]
        for row in registros:
            val = str(row.get(col_name, "")).strip()
            if val and val not in lista:
                lista.append(val)
        return lista
    except Exception as e:
        import streamlit as st
        st.error(f"Error al cargar catálogo {hoja_catalogo}: {e}")
        return ["SELECCIONE UNA OPCIÓN"]
