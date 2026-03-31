import streamlit as st
from modulos.sheets_db import (
    buscar_cliente_por_rfc,
    guardar_pedido_y_actualizar_t2,
    inyectar_t2_existente,
    buscar_contacto_externo,
    obtener_datos_pedido_por_id,
    obtener_url_impresion,
    obtener_url_pld_completo
)
from modulos.pdf_generator import generar_solicitud_pdf
from modulos.ocr_processor import extraer_datos_memoria

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Gestor de Créditos Nissan", layout="wide")
st.title("🏦 Sistema de Gestión de Créditos y Pedidos")

# --- LISTAS DE OPCIONES ---
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
# --- TAB 2: MÓDULO DE PEDIDO Y CONSTANCIA ---
with tab2:
    st.header("Validación de Constancia y Formato de Pedido")

    # 1. Botón de reset manual en sidebar
    if st.sidebar.button("♻️ Limpiar Formulario / Nuevo Registro"):
        st.session_state.datos_extraidos = {}
        st.rerun()

    # 2. El Radio Button
    opcion_pedido = st.radio("Seleccione una acción para el Pedido:", [
                             "Opción A: Nuevo Cliente (Subir Constancia)",
                             "Opción B: Cliente Existente (Inyectar ID en T2)"])

    # 3. LÓGICA DE AUTO-LIMPIEZA (Solo al cambiar de B a A)
    if "opcion_anterior" not in st.session_state:
        st.session_state.opcion_anterior = opcion_pedido

    if st.session_state.opcion_anterior == "Opción B: Cliente Existente (Inyectar ID en T2)" and \
       opcion_pedido == "Opción A: Nuevo Cliente (Subir Constancia)":
        st.session_state.datos_extraidos = {}
        st.session_state.opcion_anterior = opcion_pedido
        st.rerun()

    st.session_state.opcion_anterior = opcion_pedido

    # 4. Obtenemos los datos actuales de la memoria
    datos = st.session_state.get("datos_extraidos", {})

    # --- INICIO DE BLOQUES DE OPCIÓN ---
    if opcion_pedido == "Opción A: Nuevo Cliente (Subir Constancia)":
        archivo = st.file_uploader("Sube la Constancia de Situación Fiscal",
                                   type=["pdf", "jpg", "png", "jpeg"])

        if archivo is not None:
            # Solo procesamos si la memoria está vacía o si pedimos Reprocesar
            # Usamos una marca para saber si el archivo ya se procesó
            if not datos or st.sidebar.button("🔄 Reprocesar"):
                with st.spinner("Procesando documento..."):
                    bytes_data = archivo.read()
                    st.session_state.datos_extraidos = extraer_datos_memoria(
                        bytes_data, archivo.name.lower().endswith('.pdf'))
                    st.rerun()

    elif opcion_pedido == "Opción B: Cliente Existente (Inyectar ID en T2)":
        st.subheader("🔍 Gestión de Pedidos Existentes")
        col_b1, col_b2 = st.columns([3, 1])
        with col_b1:
            id_existente = st.text_input(
                "Ingrese el ID_Seguimiento (Ej. PED-005):")
        with col_b2:
            if st.button("📂 Cargar Datos", use_container_width=True):
                if id_existente:
                    with st.spinner("Sincronizando..."):
                        datos_rec = obtener_datos_pedido_por_id(
                            id_existente.upper())
                        if datos_rec:
                            st.session_state.datos_extraidos = datos_rec
                            inyectar_t2_existente(id_existente.upper())
                            st.rerun()
                        else:
                            st.error("❌ ID no encontrado.")

    # --- FORMULARIO DINÁMICO ---
    # Si hay datos (de la opción A o B), mostramos el formulario
    # if datos:
    if datos or opcion_pedido == "Opción A: Nuevo Cliente (Subir Constancia)":
        st.divider()
        # Buscar contacto si es nuevo cliente y tenemos RFC
        rfc_detectado = datos.get("RFC:", "")
        if rfc_detectado and "Correo Electrónico" not in datos:
            correo_ext, celular_ext = buscar_contacto_externo(rfc_detectado)
            datos["Correo Electrónico"] = correo_ext
            datos["Número Celular"] = celular_ext

        # --- SECCIÓN 1: IDENTIFICACIÓN Y OCUPACIÓN ---
        st.subheader("📋 Documentación y Ocupación")
        col_c1, col_c2, col_c3, col_c4 = st.columns(4)
        with col_c1:
            ident_idx = OPCIONES_IDENTIFICACION.index(datos.get("Identificaciones")) if datos.get(
                "Identificaciones") in OPCIONES_IDENTIFICACION else 0
            ident_sel = st.selectbox(
                "Tipo Identificación:", OPCIONES_IDENTIFICACION, index=ident_idx)
        with col_c2:
            emis_idx = OPCIONES_EMISION.index(datos.get("EMISION")) if datos.get(
                "EMISION") in OPCIONES_EMISION else 0
            emis_sel = st.selectbox(
                "Institución Emisora:", OPCIONES_EMISION, index=emis_idx)
        with col_c3:
            folio_val = st.text_input(
                "Folio ID:", value=datos.get("FOLIO", ""))
        with col_c4:
            ocupacion_val = st.text_input(
                "Ocupación:", value=datos.get("OCUPACION", ""))

        # --- SECCIÓN 2: UNIDAD Y VENTA ---
        st.subheader("🚗 Detalles de la Unidad y Financiamiento")
        col_a1, col_a2, col_a3, col_a4 = st.columns(4)
        with col_a1:
            auto_val = st.text_input("Modelo:", value=datos.get("Auto", ""))
            año_val = st.text_input("Año:", value=datos.get("AÑO", ""))
            precio_val = st.number_input("Precio Lista:", value=float(datos.get(
                "Precio Auto", 0.0)) if datos.get("Precio Auto") else 0.0, step=1000.0)
        with col_a2:
            color_val = st.text_input("Color:", value=datos.get("Color", ""))
            pago_ini_val = st.number_input("Enganche:", value=float(datos.get(
                "Pago Inicial", 0.0)) if datos.get("Pago Inicial") else 0.0, step=1000.0)
            monto_fin_val = st.number_input("Monto a Financiar:", value=float(datos.get(
                "Monto a Financiar", 0.0)) if datos.get("Monto a Financiar") else 0.0, step=1000.0)
        with col_a3:
            plazos = ["12", "18", "24", "36", "48", "60", "72", "CONTADO"]
            p_idx = plazos.index(str(datos.get("Plazo"))) if str(
                datos.get("Plazo")) in plazos else 0
            plazo_val = st.selectbox("Plazo:", plazos, index=p_idx)
            mensualidad_val = st.number_input("Mensualidad:", value=float(datos.get(
                "Mensualidades", 0.0)) if datos.get("Mensualidades") else 0.0, step=100.0)
        with col_a4:
            fin_opciones = ["FINANCIERA PROPIA", "CONTADO",
                            "BANCARIO", "KUNA", "SICREA", "OTRO"]
            # Pre-seleccionar canales
            seleccionados = [
                opt for opt in fin_opciones if datos.get(opt) == "SÍ"]
            tipo_fin = st.multiselect(
                "Canal de Venta:", fin_opciones, default=seleccionados)

        # --- Detalles de CFDI y depositos ---
        with st.expander("Datos de Facturación y Pago", expanded=True):
            col1, col2, col3 = st.columns(3)
            with col1:
                uso_cfdi = st.text_input(
                    "Uso de CFDI:", value=datos.get("USO_CFDI", ""))
            with col2:
                met_pago = st.text_input(
                    "Método de Pago:", value=datos.get("MET_PAGO", ""))
            with col3:
                anticipo = st.text_input(
                    "Anticipo:", value=datos.get("ANTICIPO", ""))

        # --- SECCIÓN 3: ADICIONALES Y TOMA ---
        st.subheader("🛠️ Adicionales y Toma de Unidad")
        c1, c2, c3 = st.columns(3)
        with c1:
            garantia_val = st.number_input("Garantía Extendida $:", value=float(datos.get(
                "GARANTIA EXTENDIDA", 0.0)) if datos.get("GARANTIA EXTENDIDA") else 0.0)
            seguro_val = st.number_input("Seguro $:", value=float(
                datos.get("SEGURO", 0.0)) if datos.get("SEGURO") else 0.0)
            toma_auto_val = st.text_input(
                "Unidad que se toma:", value=datos.get("TOMA DE AUTO", ""))
        with c2:
            kit_val = st.number_input("Kit de Seguridad $:", value=float(
                datos.get("KIT DE SEGURIDAD", 0.0)) if datos.get("KIT DE SEGURIDAD") else 0.0)
            gestoria_val = st.number_input("Gestoría $:", value=float(
                datos.get("GESTORIA", 0.0)) if datos.get("GESTORIA") else 0.0)
            precio_toma_val = st.number_input("Precio de Toma $:", value=float(
                datos.get("PRECIO DE TOMA", 0.0)) if datos.get("PRECIO DE TOMA") else 0.0)
        with c3:
            verif_val = st.number_input("Verificación $:", value=float(
                datos.get("VERIFICACION", 0.0)) if datos.get("VERIFICACION") else 0.0)
            acc_val = st.number_input("Accesorios $:", value=float(
                datos.get("ACCESORIOS", 0.0)) if datos.get("ACCESORIOS") else 0.0)
            placas_val = st.number_input("Placas / Tenencia $:", value=float(datos.get(
                "PLACAS / TENENCIA", 0.0)) if datos.get("PLACAS / TENENCIA") else 0.0)

        # --- SECCIÓN 4: AUTORIZACIONES ---
        st.subheader("✍️ Autorizaciones")
        ca1, ca2 = st.columns(2)
        with ca1:
            gerente_semi = st.text_input(
                "Gerente de Autos Seminuevos:",
                value=datos.get("GERENTE DE AUTOS SEMINUEVOS",
                                "")  # <--- Agregamos "AUTOS"
            )
        with ca2:
            gerente_ventas = st.text_input(
                "Gerente de Ventas:",
                value=datos.get("GERENTE DE VENTAS", "")
            )

        # --- SECCIÓN 5: REVISIÓN SAT ---
        with st.expander("🏠 Revisar Datos SAT (Dirección y Vialidad)"):
            datos_validados = {}
            # Filtrar llaves que no son de formulario interno
            llaves_sat = [k for k in datos.keys() if k not in fin_opciones + ["ID_Seguimiento", "EMISION", "FOLIO", "OCUPACION", "Auto", "AÑO", "Precio Auto", "Color", "Pago Inicial", "Plazo", "Mensualidades", "Monto a Financiar",
                                                                              "GARANTIA EXTENDIDA", "SEGURO", "KIT DE SEGURIDAD", "GESTORIA", "PLACAS / TENENCIA", "VERIFICACION", "ACCESORIOS", "TOMA DE AUTO", "PRECIO DE TOMA", "GERENTE DE AUTOS SEMINUEVOS", "GERENTE DE VENTAS", "Identificaciones", "USO_CFDI", "MET_PAGO", "ANTICIPO"]]

            cols_sat = st.columns(2)
            for i, k in enumerate(llaves_sat):
                with cols_sat[i % 2]:
                    datos_validados[k] = st.text_input(
                        f"Validar {k}", value=datos.get(k, ""))

        # --- BOTÓN DE CIERRE ---
        if st.button("Confirmar y Guardar Cambios"):
            if ident_sel == "SELECCIONE UNA OPCIÓN":
                st.error("❌ Por favor, selecciona un Tipo de Identificación.")
            else:
                # DETECTAR SI ES EDICIÓN:
                # Si 'datos' tiene 'ID_Seguimiento', significa que cargamos uno existente.
                id_a_editar = datos.get("ID_Seguimiento")

                with st.spinner("Guardando en Sheets..."):
                    # Consolidación final con llaves idénticas al mapeo
                    datos_finales = {**datos_validados}
                    datos_finales.update({
                        "Identificaciones": ident_sel, "EMISION": emis_sel, "FOLIO": folio_val,
                        "OCUPACION": ocupacion_val, "Auto": auto_val, "AÑO": año_val,
                        "Precio Auto": precio_val, "Color": color_val, "Pago Inicial": pago_ini_val,
                        "Plazo": plazo_val, "Mensualidades": mensualidad_val, "Monto a Financiar": monto_fin_val,
                        "FINANCIER PROPIA": "SÍ" if "FINANCIERA PROPIA" in tipo_fin else "",
                        "CONTADO": "SÍ" if "CONTADO" in tipo_fin else "",
                        "BANCARIO": "SÍ" if "BANCARIO" in tipo_fin else "",
                        "KUNA": "SÍ" if "KUNA" in tipo_fin else "",
                        "SICREA": "SÍ" if "SICREA" in tipo_fin else "",
                        "OTRO": "SÍ" if "OTRO" in tipo_fin else "",
                        "GARANTIA EXTENDIDA": garantia_val if garantia_val > 0 else "",
                        "SEGURO": seguro_val if seguro_val > 0 else "",
                        "KIT DE SEGURIDAD": kit_val if kit_val > 0 else "",
                        "GESTORIA": gestoria_val if gestoria_val > 0 else "",
                        "PLACAS / TENENCIA": placas_val if placas_val > 0 else "",
                        "VERIFICACION": verif_val if verif_val > 0 else "",
                        "ACCESORIOS": acc_val if acc_val > 0 else "",
                        "TOMA DE AUTO": toma_auto_val,
                        "PRECIO DE TOMA": precio_toma_val if precio_toma_val > 0 else "",
                        "GERENTE DE AUTOS SEMINUEVOS": gerente_semi,  # <--- Corregido con "AUTOS"
                        "GERENTE DE VENTAS": gerente_ventas,
                        "USO_CFDI": uso_cfdi,
                        "MET_PAGO": met_pago,
                        "ANTICIPO": anticipo
                    })

                    # LLAMADA A LA FUNCIÓN (Enviamos el ID si existe)
                    # Nota: Debes ajustar tu función en sheets_db.py para que acepte este segundo parámetro
                    id_gen = guardar_pedido_y_actualizar_t2(
                        datos_finales, id_actualizar=id_a_editar)
                    if id_a_editar:
                        st.success(
                            f"✅ Pedido {id_a_editar} ACTUALIZADO correctamente.")
                    else:
                        st.success(f"✅ Nuevo Pedido {id_gen} registrado.")

                    st.balloons()

        st.divider()
        st.subheader("🖨️ Formatos para Impresión")
        cp1, cp2, cp3 = st.columns(3)
        with cp1:
            st.link_button("📄 Imprimir Pedido Nissan", obtener_url_impresion(
                "Pedido"), use_container_width=True)
        with cp2:
            st.link_button("📄 Imprimir Pedido Stellantis", obtener_url_impresion(
                "pedido_stellantis"), use_container_width=True)
        with cp3:
            st.link_button("🛡️ Imprimir Formatos PLD",
                           obtener_url_pld_completo(), use_container_width=True)
