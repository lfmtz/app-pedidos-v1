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
            st.error(
                "❌ No se encontró el archivo 'credenciales.json'. Asegúrate de que esté en la carpeta principal.")
            st.stop()

    creds_dict = json.loads(creds_json)
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
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

    # --- CORRECCIÓN AQUÍ: No sobrescribir datos_constancia ---
    # Guardamos el ID en el diccionario para que se mapee a la columna 1
    datos_constancia["ID_Seguimiento"] = id_seguimiento

    # Mapeo de columnas
    mapeo = {
        "ID_Seguimiento": 1, "Nombre (s):": 2, "Primer Apellido:": 3,
        "Segundo Apellido:": 4, "RFC:": 5, "CURP:": 6, "Nombre de Vialidad:": 7,
        "Tipo de Vialidad:": 8, "Número Exterior:": 9, "Número Interior:": 10,
        "Nombre de la Colonia:": 11, "Nombre de la Localidad:": 12,
        "Nombre del Municipio o Demarcación Territorial:": 13,
        "Nombre de la Entidad Federativa:": 14, "Código Postal:": 15,
        "Correo Electrónico": 16, "Número Celular": 17
    }

    # Inserción de datos
    for campo, valor in datos_constancia.items():
        if campo in mapeo:
            columna = mapeo[campo]  # CORRECCIÓN: Usar el valor del mapeo
            sheet_pedido.update_cell(
                nueva_fila_num, columna, str(valor).upper())

    # ACTUALIZACIÓN DE CELDA T2
    sheet_formato.update(values=[[id_seguimiento]], range_name='T2')

    return id_seguimiento


def inyectar_t2_existente(id_seguimiento):
    client = get_client()
    doc_pedido = client.open("FORMATO DE PEDIDO_26")
    sheet_formato = doc_pedido.worksheet("Pedido")
    sheet_formato.update(values=[[id_seguimiento]], range_name='T2')


def buscar_contacto_externo(rfc_busqueda):
    """
    Busca en SOL_CREDITO_ACTUAL_2026 el correo y celular asociados al RFC.
    """
    try:
        client = get_client()
        sheet_base = client.open("SOL_CREDITO_ACTUAL_2026").sheet1

        # Localizar la celda del RFC
        celda = sheet_base.find(rfc_busqueda.strip().upper())

        # Obtener los valores de esa fila
        fila_valores = sheet_base.row_values(celda.row)

        # Según tu lógica: índice 12 (columna 13) celular, índice 13 (columna 14) correo
        celular = fila_valores[12] if len(fila_valores) > 12 else ""
        correo = fila_valores[13] if len(fila_valores) > 13 else ""

        return correo, celular
    except Exception:
        # Si no se encuentra el RFC o hay error, devolvemos vacío para llenado manual
        return "", ""
