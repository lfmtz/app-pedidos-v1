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

    # Agregamos el ID al diccionario para el mapeo
    datos_constancia["ID_Seguimiento"] = id_seguimiento

    # --- MAPEO CORREGIDO ---
    # Asegúrate de que los nombres de las llaves coincidan EXACTAMENTE con app.py
    mapeo = {
        "ID_Seguimiento": 1,
        "Nombre (s):": 2,
        "Primer Apellido:": 3,
        "Segundo Apellido:": 4,
        "RFC:": 5,
        "CURP:": 6,
        # <--- Aquí estaba el detalle de inyección
        "Nombre de Vialidad (Calle):": 7,
        "Tipo de Vialidad:": 8,
        "Número Exterior:": 9,
        "Número Interior:": 10,
        "Nombre de la Colonia:": 11,
        "Nombre de la Localidad:": 12,
        "Nombre del Municipio o Demarcación Territorial:": 13,
        "Nombre de la Entidad Federativa:": 14,
        "Código Postal:": 15,
        "Correo Electrónico": 16,
        "Número Celular": 17,
        "Identificaciones": 18,
        "EMISION": 19,
        "FOLIO": 20,
        "Auto": 21,
        "Precio Auto": 22,
        "Color": 23,
        "Pago Inicial": 24,
        "Plazo": 25,
        "Mensualidades": 26,
        "Monto a Financiar": 27,
        "AÑO": 28,
        "OCUPACION": 29,
        "FINANCIER PROPIA": 30,
        "CONTADO": 31,
        "BANCARIO": 32,
        "KUNA": 33,
        "OTRO": 34,
        "SICREA": 35,
        "GARANTIA EXTENDIDA": 36,
        "SEGURO": 37,
        "KIT DE SEGURIDAD": 38,
        "GESTORIAPLACAS / TENENCIA": 39,
        "VERIFICACION": 40,
        "ACCESORIOS": 41,
        "TOMA DE AUTO": 42,
        "PRECIO DE TOMA": 43,
        "GERENTE DE SEMINUEVOS": 44,
        "GERENTE DE VENTAS": 45
    }

    # --- INSERCIÓN EFICIENTE ---
    # En lugar de update_cell uno por uno (que es lento), preparamos una fila
    max_col = max(mapeo.values())
    fila_a_inyectar = [""] * max_col

    for campo, valor in datos_constancia.items():
        if campo in mapeo:
            idx = mapeo[campo] - 1  # Ajuste a índice 0
            fila_a_inyectar[idx] = str(valor).upper()

    sheet_pedido.append_row(fila_a_inyectar)

    # Actualización de celda T2 (Formato Nuevo)
    sheet_formato.update(range_name='T2', values=[[id_seguimiento]])

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
