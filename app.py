import streamlit as st
from modulos.sheets_db import buscar_cliente_por_rfc, guardar_pedido_y_actualizar_t2, inyectar_t2_existente, buscar_contacto_externo
from modulos.pdf_generator import generar_solicitud_pdf
from modulos.ocr_processor import extraer_datos_memoria

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Gestor de Créditos", layout="wide")
st.title("🏦 Sistema de Gestión de Créditos y Pedidos")

# --- LISTAS DE OPCIONES PARA COMBOS ---
OPCIONES_IDENTIFICACION = [
    "SELECCIONE UNA OPCIÓN", "CREDENCIAL PARA VOTAR", "PASAPORTE",
    "Tarjeta de Residente Temporal", "Tarjeta de Residente Permanente",
    "Tarjeta de Visitante por Razones Humanitarianas", "CARTILLA MILITAR", "CEDULA PROFESIONAL"
]

OPCIONES_EMISION = [
    "SELECCIONE UNA OPCIÓN", "INSTITUTO NACIONAL DE MIGRACION", "INSTITUTO NACIONAL ELECTORAL",
    "SECRETARIA DE RELACIONES EXTERIORES", "SECRETARIA DE EDUCACION PUBLICA"
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
                    st.download_button(label="📥 Descargar Solicitud PDF", data=pdf_file,
                                       file_name=f"Solicitud_{rfc_input.upper()}.pdf", mime="application/pdf")
                else:
                    st.error("Cliente no encontrado en SOL_CREDITO_ACTUAL_2026.")
        else:
            st.warning("Por favor ingrese un RFC.")

# --- TAB 2: MÓDULO DE PEDIDO Y CONSTANCIA ---
with tab2:
    st.header("Validación de Constancia y Formato de Pedido")
    opcion_pedido = st.radio("Seleccione una acción para el Pedido:", [
                             "Opción A: Nuevo Cliente (Subir Constancia)", "Opción B: Cliente Existente (Inyectar ID en T2)"])

    if opcion_pedido == "Opción A: Nuevo Cliente (Subir Constancia)":
        archivo = st.file_uploader("Sube la Constancia de Situación Fiscal", type=[
                                   "pdf", "jpg", "png", "jpeg"])

        if archivo is not None:
            if "datos_extraidos" not in st.session_state or st.sidebar.button("🔄 Reprocesar"):
                with st.spinner("Procesando documento..."):
                    bytes_data = archivo.read()
                    is_pdf = archivo.name.lower().endswith('.pdf')
                    st.session_state.datos_extraidos = extraer_datos_memoria(
                        bytes_data, is_pdf)

            if st.session_state.datos_extraidos:
                datos = st.session_state.datos_extraidos
                rfc_detectado = datos.get("RFC:", "")
                if rfc_detectado and "Correo Electrónico" not in datos:
                    correo_ext, celular_ext = buscar_contacto_externo(
                        rfc_detectado)
                    datos["Correo Electrónico"] = correo_ext
                    datos["Número Celular"] = celular_ext

                st.divider()

                # --- SECCIÓN 1: IDENTIFICACIÓN Y DATOS PERSONALES ---
                st.subheader("📋 Documentación y Ocupación")
                col_c1, col_c2, col_c3, col_c4 = st.columns(4)
                with col_c1:
                    ident_sel = st.selectbox(
                        "Tipo Identificación:", OPCIONES_IDENTIFICACION)
                with col_c2:
                    emis_sel = st.selectbox(
                        "Institución Emisora:", OPCIONES_EMISION)
                with col_c3:
                    folio_val = st.text_input("Folio ID (Elector/Pasaporte):")
                with col_c4:
                    ocupacion_val = st.text_input("Ocupación del Cliente:")

                st.markdown("---")

                # --- SECCIÓN 2: DATOS DE LA UNIDAD Y VENTA ---
                st.subheader("🚗 Detalles de la Unidad y Financiamiento")
                col_a1, col_a2, col_a3, col_a4 = st.columns(4)
                with col_a1:
                    auto_val = st.text_input("Modelo (ej. Sentra):")
                    año_val = st.text_input("Año:")
                    precio_val = st.number_input(
                        "Precio Lista:", min_value=0.0, step=1000.0)
                with col_a2:
                    color_val = st.text_input("Color:")
                    pago_ini_val = st.number_input(
                        "Pago Inicial (Enganche):", min_value=0.0, step=1000.0)
                    monto_fin_val = st.number_input(
                        "Monto a Financiar:", min_value=0.0, step=1000.0)
                with col_a3:
                    plazo_val = st.selectbox(
                        "Plazo:", ["12", "18", "24", "36", "48", "60", "72", "CONTADO"])
                    mensualidad_val = st.number_input(
                        "Mensualidad:", min_value=0.0, step=100.0)
                with col_a4:
                    st.write("**Canal de Venta / Financiera:**")
                    tipo_fin = st.multiselect("Seleccione opciones:", [
                                              "FINANCIERA PROPIA", "CONTADO", "BANCARIO", "KUNA", "SICREA", "OTRO"])

                st.divider()

                # --- SECCIÓN 3: ADICIONALES Y TRÁMITES ---
                st.subheader("🛠️ Adicionales, Gestoría y Toma")
                c1, c2, c3 = st.columns(3)
                with c1:
                    garantia_ext = st.checkbox("Garantía Extendida")
                    seguro_auto = st.checkbox("Seguro")
                    kit_seguridad = st.checkbox("Kit de Seguridad")
                with c2:
                    gestoria = st.checkbox("Gestoría Placas / Tenencia")
                    verificacion = st.checkbox("Verificación")
                    accesorios = st.checkbox("Accesorios")
                with c3:
                    toma_auto = st.checkbox("Toma de Auto")
                    precio_toma = st.number_input(
                        "Precio de Toma:", min_value=0.0)

                st.divider()

                # --- SECCIÓN 4: AUTORIZACIONES Y DATOS SAT ---
                st.subheader("✍️ Autorizaciones y Validación SAT")
                ca1, ca2 = st.columns(2)
                with ca1:
                    gerente_semi = st.text_input(
                        "Gerente de Autos Seminuevos:")
                with ca2:
                    gerente_ventas = st.text_input("Gerente de Ventas:")

                with st.expander("🏠 Revisar Datos SAT Extraídos"):
                    datos_validados = {}
                    cols_sat = st.columns(2)
                    for i, (k, v) in enumerate(datos.items()):
                        with cols_sat[i % 2]:
                            datos_validados[k] = st.text_input(
                                f"Validar {k}", value=v)

                # --- BOTÓN DE CIERRE ---
                if st.button("Confirmar y Generar Pedido"):
                    if ident_sel == "SELECCIONE UNA OPCIÓN":
                        st.error(
                            "❌ Por favor, selecciona un Tipo de Identificación.")
                    else:
                        with st.spinner("Guardando expediente completo en Sheets..."):
                            datos_validados.update({
                                "Identificaciones": ident_sel, "EMISION": emis_sel, "FOLIO": folio_val,
                                "Auto": auto_val, "AÑO": año_val, "Precio Auto": precio_val, "Color": color_val,
                                "OCUPACION": ocupacion_val, "Pago Inicial": pago_ini_val, "Plazo": plazo_val,
                                "Mensualidades": mensualidad_val, "Monto a Financiar": monto_fin_val,
                                "FINANCIERA PROPIA": "SÍ" if "FINANCIERA PROPIA" in tipo_fin else "NO",
                                "CONTADO": "SÍ" if "CONTADO" in tipo_fin else "NO",
                                "BANCARIO": "SÍ" if "BANCARIO" in tipo_fin else "NO",
                                "KUNA": "SÍ" if "KUNA" in tipo_fin else "NO",
                                "SICREA": "SÍ" if "SICREA" in tipo_fin else "NO",
                                "OTRO": "SÍ" if "OTRO" in tipo_fin else "NO",
                                "GARANTIA EXTENDIDA": "SÍ" if garantia_ext else "NO",
                                "SEGURO": "SÍ" if seguro_auto else "NO",
                                "KIT DE SEGURIDAD": "SÍ" if kit_seguridad else "NO",
                                "GESTORIAPLACAS / TENENCIA": "SÍ" if gestoria else "NO",
                                "VERIFICACION": "SÍ" if verificacion else "NO",
                                "ACCESORIOS": "SÍ" if accesorios else "NO",
                                "TOMA DE AUTO": "SÍ" if toma_auto else "NO",
                                "PRECIO DE TOMA": precio_toma,
                                "GERENTE DE AUTOS SEMINUEVOS": gerente_semi,
                                "GERENTE DE VENTAS": gerente_ventas
                            })
                            id_gen = guardar_pedido_y_actualizar_t2(
                                datos_validados)
                            st.success(
                                f"✅ ¡Expediente {id_gen} registrado con éxito!")
                            st.balloons()

    elif opcion_pedido == "Opción B: Cliente Existente (Inyectar ID en T2)":
        id_existente = st.text_input(
            "Ingrese el ID_Seguimiento (Ej. PED-005):")
        if st.button("Actualizar Formato (T2)"):
            if id_existente:
                with st.spinner("Actualizando T2..."):
                    inyectar_t2_existente(id_existente.upper())
                    st.success(
                        f"✅ Celda T2 actualizada con {id_existente.upper()}.")
