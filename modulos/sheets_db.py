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


def guardar_pedido_y_actualizar_t2(datos_constancia):
    client = get_client()
    doc_pedido = client.open("FORMATO DE PEDIDO_26")
    sheet_pedido = doc_pedido.worksheet("datos_pedidos")
    sheet_formato = doc_pedido.worksheet("Pedido")

    todas_las_filas = sheet_pedido.get_all_values()
    nueva_fila_num = len(todas_las_filas) + 1
    id_seguimiento = f"PED-{nueva_fila_num:03d}"

    # 1. NORMALIZACIÓN AGRESIVA
    def limpiar_texto(texto):
        if not texto:
            return ""
        # Quitamos puntos, paréntesis y espacios, pasamos a MAYÚSCULAS
        return str(texto).replace(":", "").replace("(", "").replace(")", "").strip().upper()

    datos_limpios = {limpiar_texto(k): v for k, v in datos_constancia.items()}
    datos_limpios["ID_SEGUIMIENTO"] = id_seguimiento

    # 2. MAPEO SIN CARACTERES ESPECIALES
    # --- MAPEO ALFABÉTICO CORREGIDO (SEGÚN IMÁGENES) ---
    # Asegúrate de que las llaves (ej. "RFC:") coincidan exactamente con tu app.py
    mapeo = {
        # Sección A - J (Imagen 1)
        "ID_Seguimiento": 1,        # Columna A
        "Nombre (s):": 2,          # Columna B
        "Primer Apellido:": 3,     # Columna C
        "Segundo Apellido:": 4,    # Columna D
        "RFC:": 5,                  # Columna E
        "CURP:": 6,                 # Columna F
        "Nombre de Vialidad (Calle):": 7,  # Columna G
        "Tipo de Vialidad:": 8,    # Columna H
        "Número Exterior:": 9,      # Columna I
        "Número Interior:": 10,     # Columna J

        # Sección K - V (Imagen 2)
        "Nombre de la Colonia:": 11,  # Columna K
        "Nombre de la Localidad:": 12,  # Columna L
        "Nombre del Municipio o Demarcación Territorial:": 13,  # Columna M
        "Nombre de la Entidad Federativa:": 14,  # Columna N
        "Código Postal:": 15,       # Columna O
        "Correo Electrónico": 16,   # Columna P
        "Número Celular": 17,       # Columna Q
        "Identificaciones": 18,     # Columna R
        "EMISION": 19,               # Columna S
        "FOLIO": 20,                 # Columna T
        "Auto": 21,                  # Columna U
        "Precio Auto": 22,           # Columna V

        # Sección intermedia W - AM (No mostrada, asumimos correlativas)
        "Color": 23,                 # Columna W
        "Pago Inicial": 24,         # Columna X
        "Plazo": 25,                 # Columna Y
        "Mensualidades": 26,         # Columna Z
        "Monto a Financiar": 27,    # Columna AA
        "AÑO": 28,                  # Columna AB
        "OCUPACION": 29,            # Columna AC
        "FINANCIER PROPIA": 30,     # Columna AD
        "CONTADO": 31,              # Columna AE
        "BANCARIO": 32,             # Columna AF
        "KUNA": 33,                  # Columna AG
        "SICREA": 34,                # Columna AH
        "OTRO": 35,                  # Columna AI
        "GARANTIA EXTENDIDA": 36,   # Columna AJ
        "SEGURO": 37,                # Columna AK
        "KIT DE SEGURIDAD": 38,     # Columna AL
        # Columna AM (Ojo: según imagen 3, AM es Verificación)
        "VERIFICACION": 39,

        # Sección AN - AU (Imagen 3)
        "GESTORIAPLACAS / TENENCIA": 40,  # Columna AN (PLACAS / T)
        "ACCESORIOS": 41,                # Columna AP
        "TOMA DE AUTO": 42,              # Columna AQ
        "PRECIO DE TOMA": 43,            # Columna AR
        "GERENTE DE SEMINUEVOS": 44,     # Columna AS
        "GERENTE DE VENTAS": 45          # Columna AT/AU
    }

    fila_a_inyectar = [""] * 45

    # 3. REFUERZO PARA VIALIDAD (Si el OCR detecta variaciones, las unificamos en la columna 7)
    posibles_vialidades = ["NOMBRE DE VIALIDAD",
                           "VIALIDAD", "CALLE", "NOMBRE DE VIALIDAD CALLE"]
    for p in posibles_vialidades:
        if p in datos_limpios and datos_limpios[p]:
            datos_limpios["NOMBRE DE VIALIDAD CALLE"] = datos_limpios[p]
            break

    # 4. LLENADO DE FILA POR POSICIÓN
    for campo, valor in datos_limpios.items():
        if campo in mapeo:
            columna_idx = mapeo[campo] - 1
            fila_a_inyectar[columna_idx] = str(valor).upper()

    # 5. INYECCIÓN
    sheet_pedido.append_row(fila_a_inyectar)

    # Intento de actualización de T2 (con manejo de error por si la versión de gspread varía)
    try:
        sheet_formato.update(values=[[id_seguimiento]], range_name='T2')
    except:
        sheet_formato.update('T2', [[id_seguimiento]])

    return id_seguimiento


def inyectar_t2_existente(id_seguimiento):
    client = get_client()
    doc_pedido = client.open("FORMATO DE PEDIDO_26")
    sheet_formato = doc_pedido.worksheet("Pedido")
    sheet_formato.update(range_name='T2', values=[[id_seguimiento]])


def buscar_contacto_externo(rfc_busqueda):
    try:
        client = get_client()
        sheet_base = client.open("SOL_CREDITO_ACTUAL_2026").sheet1
        celda = sheet_base.find(rfc_busqueda.strip().upper())
        fila_valores = sheet_base.row_values(celda.row)
        # Ajuste de índices: 12=Celular, 13=Correo
        celular = fila_valores[12] if len(fila_valores) > 12 else ""
        correo = fila_valores[13] if len(fila_valores) > 13 else ""
        return correo, celular
    except:
        return "", ""
