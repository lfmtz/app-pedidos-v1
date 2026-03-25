import streamlit as st
from modulos.sheets_db import buscar_cliente_por_rfc, guardar_pedido_y_actualizar_t2, inyectar_t2_existente, buscar_contacto_externo
from modulos.pdf_generator import generar_solicitud_pdf
from modulos.ocr_processor import extraer_datos_memoria

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Gestor de Créditos", layout="wide")
st.title("🏦 Sistema de Gestión de Créditos y Pedidos")

# --- LISTAS DE OPCIONES PARA COMBOS ---
OPCIONES_IDENTIFICACION = [
    "SELECCIONE UNA OPCIÓN",
    "CREDENCIAL PARA VOTAR",
    "PASAPORTE",
    "Tarjeta de Residente Temporal",
    "Tarjeta de Residente Permanente",
    "Tarjeta de Visitante por Razones Humanitarianas",
    "CARTILLA MILITAR",
    "CEDULA PROFESIONAL"
]

OPCIONES_EMISION = [
    "SELECCIONE UNA OPCIÓN",
    "INSTITUTO NACIONAL DE MIGRACION",
    "INSTITUTO NACIONAL ELECTORAL",
    "SECRETARIA DE RELACIONES EXTERIORES",
    "SECRETARIA DE EDUCACION PUBLICA"
]

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
                        f"Cliente encontrado: {cliente.get('Nombre(s) accredited', '')}")
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
        archivo = st.file_uploader("Sube la Constancia de Situación Fiscal", type=[
                                   "pdf", "jpg", "png", "jpeg"])

        if archivo is not None:
            # 1. PROCESAMIENTO CON PERSISTENCIA
            if "datos_extraidos" not in st.session_state or st.sidebar.button("🔄 Reprocesar"):
                with st.spinner("Procesando documento..."):
                    bytes_data = archivo.read()
                    is_pdf = archivo.name.lower().endswith('.pdf')
                    st.session_state.datos_extraidos = extraer_datos_memoria(
                        bytes_data, is_pdf)

            # 2. CUADRO DE DEBUG
            with st.expander("🔍 DEBUG: Ver datos extraídos"):
                if st.session_state.datos_extraidos:
                    st.json(st.session_state.datos_extraidos)
                else:
                    st.write("No se capturó texto")

            # 3. INTERFAZ DE VALIDACIÓN E INYECCIÓN
            if st.session_state.datos_extraidos:
                datos = st.session_state.datos_extraidos

                # Búsqueda externa de contacto
                rfc_detectado = datos.get("RFC:", "")
                if rfc_detectado and "Correo Electrónico" not in datos:
                    correo_ext, celular_ext = buscar_contacto_externo(
                        rfc_detectado)
                    datos["Correo Electrónico"] = correo_ext
                    datos["Número Celular"] = celular_ext

                st.divider()
                st.subheader("📋 Selección de Documentos y Validación")

                # --- SECCIÓN DE COMBOS ---
                st.info("Seleccione la identificación oficial del cliente:")
                col_c1, col_c2 = st.columns(2)
                with col_c1:
                    ident_sel = st.selectbox(
                        "Identificaciones:", OPCIONES_IDENTIFICACION)
                with col_c2:
                    emis_sel = st.selectbox("EMISION:", OPCIONES_EMISION)

                st.markdown("---")

                # --- FORMULARIO DE DATOS ---
                datos_validados = {}
                col1, col2 = st.columns(2)
                for i, (k, v) in enumerate(datos.items()):
                    with col1 if i % 2 == 0 else col2:
                        datos_validados[k] = st.text_input(
                            f"Validar {k}", value=v)

                # --- BOTÓN FINAL DE CONFIRMACIÓN ---
                if st.button("Confirmar y Generar Pedido"):
                    # Validación de seguridad de los combos
                    if ident_sel == "SELECCIONE UNA OPCIÓN" or emis_sel == "SELECCIONE UNA OPCIÓN":
                        st.error(
                            "❌ Error: Debes seleccionar una Identificación y su Emisor.")
                    else:
                        with st.spinner("Inyectando en Google Sheets..."):
                            # Agregamos los combos al diccionario final
                            datos_validados["Identificaciones"] = ident_sel
                            datos_validados["EMISION"] = emis_sel

                            id_gen = guardar_pedido_y_actualizar_t2(
                                datos_validados)

                            st.success(
                                f"✅ ¡Pedido {id_gen} inyectado con éxito!")
                            st.balloons()
                            st.info(
                                "La celda T2 del formato ha sido actualizada correctamente.")

    elif opcion_pedido == "Opción B: Cliente Existente (Inyectar ID en T2)":
        id_existente = st.text_input(
            "Ingrese el ID_Seguimiento (Ej. PED-005):")
        if st.button("Actualizar Formato (T2)"):
            if id_existente:
                with st.spinner("Actualizando T2..."):
                    inyectar_t2_existente(id_existente.upper())
                    st.success(
                        f"✅ Celda T2 actualizada con {id_existente.upper()}.")
