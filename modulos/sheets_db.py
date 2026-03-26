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

    # --- MAPEO SOLICITADO (ESTRICTO) ---
    mapeo = {
        "ID_Seguimiento": 1,
        "Nombre (s):": 2,
        "Primer Apellido:": 3,
        "Segundo Apellido:": 4,
        "RFC:": 5,
        "CURP:": 6,
        "Nombre de Vialidad:": 7,
        "Tipo de Vialidad:": 8,
        "Número Exterior:": 9,
        "Número Interior:": 10,
        "Nombre de la Colonia:": 11,
        "Nombre de la Localidad:": 12,
        "Nombre del Municipio o Demarcación Territorial:": 13,
        "Nombre de la Entidad Federativa:": 14,
        "Código Postal:": 15
    }

    # Creamos la fila vacía de 45 espacios para asegurar que no se mueva nada
    fila_a_inyectar = [""] * 45

    # Aseguramos el ID de seguimiento
    datos_constancia["ID_Seguimiento"] = id_seguimiento

    # --- INYECCIÓN BASADA EN COINCIDENCIA DE LLAVE ---
    for campo, valor in datos_constancia.items():
        # Verificamos si el campo existe en nuestro mapeo estricto
        if campo in mapeo:
            columna_idx = mapeo[campo] - 1
            fila_a_inyectar[columna_idx] = str(valor).upper() if valor else ""

        # Refuerzo específico para Vialidad por si el OCR trae variaciones de nombre
        # (Esto asegura la columna 7 aunque el nombre varíe un poco)
        elif "Vialidad" in campo or "Calle" in campo:
            if fila_a_inyectar[6] == "":  # Si la columna 7 sigue vacía
                fila_a_inyectar[6] = str(valor).upper()

    # Inserción en Sheets
    try:
        sheet_pedido.append_row(fila_a_inyectar)
    except Exception as e:
        st.error(f"Error en append_row: {e}")

    # Actualización de T2
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
