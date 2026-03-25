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
    mapeo = {
        "ID_SEGUIMIENTO": 1, "NOMBRE S": 2, "PRIMER APELLIDO": 3, "SEGUNDO APELLIDO": 4,
        "RFC": 5, "CURP": 6, "NOMBRE DE VIALIDAD CALLE": 7, "TIPO DE VIALIDAD": 8,
        "NUMERO EXTERIOR": 9, "NUMERO INTERIOR": 10, "NOMBRE DE LA COLONIA": 11,
        "NOMBRE DE LA LOCALIDAD": 12, "NOMBRE DEL MUNICIPIO O DEMARCACION TERRITORIAL": 13,
        "NOMBRE DE LA ENTIDAD FEDERATIVA": 14, "CODIGO POSTAL": 15, "CORREO ELECTRONICO": 16,
        "NUMERO CELULAR": 17, "IDENTIFICACIONES": 18, "EMISION": 19, "FOLIO": 20,
        "AUTO": 21, "PRECIO AUTO": 22, "COLOR": 23, "PAGO INICIAL": 24, "PLAZO": 25,
        "MENSUALIDADES": 26, "MONTO A FINANCIAR": 27, "AÑO": 28, "OCUPACION": 29,
        "FINANCIER PROPIA": 30, "CONTADO": 31, "BANCARIO": 32, "KUNA": 33, "OTRO": 34,
        "SICREA": 35, "GARANTIA EXTENDIDA": 36, "SEGURO": 37, "KIT DE SEGURIDAD": 38,
        "GESTORIAPLACAS / TENENCIA": 39, "VERIFICACION": 40, "ACCESORIOS": 41,
        "TOMA DE AUTO": 42, "PRECIO DE TOMA": 43, "GERENTE DE SEMINUEVOS": 44,
        "GERENTE DE VENTAS": 45
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
