import streamlit as st
from modulos.sheets_db import buscar_cliente_por_rfc, guardar_pedido_y_actualizar_t2, inyectar_t2_existente, buscar_contacto_externo
from modulos.pdf_generator import generar_solicitud_pdf
from modulos.ocr_processor import extraer_datos_memoria

st.set_page_config(page_title="Gestor de Créditos", layout="wide")
st.title("🏦 Sistema de Gestión de Créditos y Pedidos")

tab1, tab2 = st.tabs(["📄 Generar Solicitud", "🔍 Validar Constancia"])

# --- TAB 1: MÓDULO DE SOLICITUD ---
with tab1:
    st.header("Generación de Solicitud PDF")
    rfc_input = st.text_input(
        "Ingrese el RFC del cliente para buscar en la base:")

    if st.button("Buscar y Generar Solicitud"):
        if rfc_input:
            with st.spinner("Buscando cliente..."):
                cliente = buscar_cliente_por_rfc(rfc_input)
                if cliente:
                    st.success(
                        f"Cliente encontrado: {cliente.get('Nombre(s) acreditado', '')}")
                    pdf_file = generar_solicitud_pdf(cliente)
                    st.download_button(
                        label="📥 Descargar Solicitud PDF",
                        data=pdf_file,
                        file_name=f"Solicitud_{rfc_input.upper()}.pdf",
                        mime="application/pdf"
                    )
                else:
                    st.error("Cliente no encontrado en SOL_CREDITO_ACTUAL_2026.")
        else:
            st.warning("Por favor ingrese un RFC.")

# --- TAB 2: MÓDULO DE PEDIDO Y CONSTANCIA ---
with tab2:
    st.header("Validación de Constancia y Formato de Pedido")

    opcion_pedido = st.radio("Seleccione una acción para el Pedido:", [
        "Opción A: Nuevo Cliente (Subir Constancia)",
        "Opción B: Cliente Existente (Inyectar ID en T2)"
    ])

    if opcion_pedido == "Opción A: Nuevo Cliente (Subir Constancia)":
        tiene_constancia = st.radio(
            "¿Cuentas con la Constancia de Situación Fiscal?", ["Sí", "No"])

        if tiene_constancia == "Sí":
            archivo = st.file_uploader("Sube la Constancia (PDF o Imagen)", type=[
                                       "pdf", "jpg", "png", "jpeg"])

            if archivo is not None:
                with st.spinner("Procesando documento con OCR..."):
                    bytes_data = archivo.read()
                    is_pdf = archivo.name.lower().endswith('.pdf')
                    # 1. Extraer datos básicos del OCR
                    datos_extraidos = extraer_datos_memoria(bytes_data, is_pdf)

                    # --- LÓGICA DE BÚSQUEDA EXTERNA (INYECCIÓN) ---
                    rfc_detectado = datos_extraidos.get("RFC:", "")
                    if rfc_detectado:
                        # Buscamos en la otra hoja si ya tenemos su contacto
                        correo_ext, celular_ext = buscar_contacto_externo(
                            rfc_detectado)

                        # Agregamos estos datos al diccionario para que aparezcan en los inputs
                        datos_extraidos["Correo Electrónico"] = correo_ext
                        datos_extraidos["Número Celular"] = celular_ext
                    # -----------------------------------------------

                st.subheader("Revisión de Datos Extraídos")
                # El usuario verá los datos del OCR + los datos inyectados de la base externa
                datos_validados = {}

                # Creamos 2 columnas para que el formulario no sea tan largo
                col1, col2 = st.columns(2)
                for i, (k, v) in enumerate(datos_extraidos.items()):
                    with col1 if i % 2 == 0 else col2:
                        datos_validados[k] = st.text_input(k, value=v)

                if st.button("Confirmar y Generar Pedido"):
                    with st.spinner("Guardando en Sheets y actualizando T2..."):
                        id_gen = guardar_pedido_y_actualizar_t2(
                            datos_validados)
                        st.success(f"✅ Datos guardados. ID Generado: {id_gen}")
                        st.info(
                            "La celda T2 ha sido actualizada. El formato de pedido está listo en Google Sheets.")
        else:
            st.info("Puedes guardar el progreso y continuar después.")

    elif opcion_pedido == "Opción B: Cliente Existente (Inyectar ID en T2)":
        id_existente = st.text_input(
            "Ingrese el ID_Seguimiento existente (Ej. PED-005):")
        if st.button("Actualizar Formato (T2)"):
            if id_existente:
                with st.spinner("Actualizando celda T2..."):
                    inyectar_t2_existente(id_existente.upper())
                    st.success(
                        f"✅ Celda T2 actualizada con {id_existente.upper()}.")
            else:
                st.warning("Ingrese un ID válido.")
