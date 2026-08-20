import streamlit as st
from modulos.sheets_db import (
    buscar_cliente_por_rfc,
    guardar_pedido_y_actualizar_t2,
    inyectar_t2_existente,
    buscar_contacto_externo,
    obtener_datos_pedido_por_id,
    obtener_url_impresion,
    obtener_url_pld,
    inyectar_datos_generico,
    actualizar_ultimo_registro_hoja,
    actualizar_campo_pld_representante,
    generar_id_especifico,
    obtener_representantes_legales,
    actualizar_representante_en_pm_stellantis,
    obtener_catalogo_ocupaciones,
    eliminar_registro_por_id,
    obtener_listado_sol_credito
)
from modulos.pdf_generator import generar_solicitud_pdf
from modulos.ocr_processor import extraer_datos_memoria
from modulos.pdf_generator import generar_pdf_aviso_privacidad
from modulos.pdf_generator import generar_pdf_stellantis

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

    # Selector de marca
    marca_sol = st.radio(
        "Seleccione la marca de la solicitud:",
        ["Nissan", "Stellantis"],
        horizontal=True,
        key="marca_selector_tab1"
    )

    # ─── BÚSQUEDA POR NOMBRE O RFC ─────────────────────────────────────────────────────────
    with st.spinner("Cargando lista de clientes..."):
        listado_sol = obtener_listado_sol_credito()

    rfc_input = ""
    if listado_sol:
        opciones_etiquetas = ["— Escribe nombre o RFC para buscar —"] + [
            c["etiqueta"] for c in listado_sol
        ]
        # mapeo etiqueta → datos del cliente
        mapa_clientes = {c["etiqueta"]: c for c in listado_sol}

        seleccion = st.selectbox(
            "🔍 Buscar cliente por nombre:",
            opciones_etiquetas,
            key="busqueda_cliente_sol"
        )
        if seleccion != "— Escribe nombre o RFC para buscar —":
            cliente_sel = mapa_clientes.get(seleccion, {})
            rfc_input = cliente_sel.get("rfc", "")
            nombre_sel = cliente_sel.get("nombre", "")
            # ── Tarjeta de confirmación ──────────────────────────────────
            st.info(
                f"**✅ Cliente seleccionado para la solicitud:**\n\n"
                f"👤 **Nombre:** {nombre_sel}\n\n"
                f"🪪 **RFC:** {rfc_input}"
            )
    else:
        # Fallback: campo manual si no hay lista
        rfc_input = st.text_input("Ingrese el RFC del cliente para buscar en la base:")
    # ────────────────────────────────────────────────────────────────────────────

    if st.button("Buscar y Generar Solicitud"):
        if rfc_input:
            with st.spinner(f"Buscando cliente y preparando solicitud de {marca_sol}..."):
                cliente = buscar_cliente_por_rfc(rfc_input)

                if cliente:
                    st.success(
                        f"Cliente encontrado: {cliente.get('Nombre(s) acreditado', '')}")

                    if marca_sol == "Nissan":
                        pdf_file = generar_solicitud_pdf(cliente)
                        nombre_final = f"Solicitud_Nissan_{rfc_input.upper()}.pdf"
                    else:
                        pdf_file, nombre_final = generar_pdf_stellantis(cliente)

                    st.download_button(
                        label=f"📥 Descargar Solicitud {marca_sol}",
                        data=pdf_file,
                        file_name=nombre_final,
                        mime="application/pdf"
                    )
                else:
                    st.error("Cliente no encontrado en SOL_CREDITO_ACTUAL_2026.")
        else:
            st.warning("👆 Selecciona un cliente de la lista para continuar.")

# --- TAB 2: MÓDULO DE PEDIDO Y CONSTANCIA ---
with tab2:
    st.header("Validación de Constancia y Formato de Pedido")

    # ─── BANDERA DE CONTROL (Backend) ───────────────────────────────────────
    # Cambia a False para ocultar el listado de clientes sin tocar el resto
    MOSTRAR_LISTADO_CLIENTES = True

    # Campos SAT para captura manual (cuando no hay constancia)
    CAMPOS_SAT = [
        "Nombre (s):", "Primer Apellido:", "Segundo Apellido:",
        "RFC:", "CURP:",
        "Tipo de Vialidad:", "Nombre de Vialidad:",
        "Número Exterior:", "Número Interior:",
        "Nombre de la Colonia:", "Nombre de la Localidad:",
        "Nombre del Municipio o Demarcación Territorial:",
        "Nombre de la Entidad Federativa:", "Código Postal:",
        "Correo Electrónico", "Número Celular"
    ]
    # ─────────────────────────────────────────────────────────────────────────

    # 2. El Radio Button
    opcion_pedido = st.radio("Seleccione una acción para el Pedido:", [
                             "Opción A: Nuevo Cliente (Subir Constancia)",
                             "Opción B: Cliente Existente (Inyectar ID en T2)",
                             "Opción C: Captura Manual (Sin Constancia)"])

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

        # Listado de clientes (controlado por la bandera MOSTRAR_LISTADO_CLIENTES)
        if MOSTRAR_LISTADO_CLIENTES:
            from modulos.sheets_db import obtener_listado_clientes
            with st.spinner("Cargando listado de clientes..."):
                listado = obtener_listado_clientes()
            if listado:
                opciones_lista = ["— Seleccionar del listado —"] + [
                    f"{c['ID_Seguimiento']} | {c.get('Nombre (s):','')} {c.get('Primer Apellido:','')}"
                    for c in listado
                ]
                sel_lista = st.selectbox("📋 Seleccionar cliente del listado:", opciones_lista, key="sel_cliente_lista")
                if sel_lista != "— Seleccionar del listado —":
                    id_de_lista = sel_lista.split(" | ")[0].strip()
                    if st.button("📂 Cargar cliente seleccionado", use_container_width=True):
                        with st.spinner("Cargando..."):
                            datos_rec = obtener_datos_pedido_por_id(id_de_lista)
                            if datos_rec:
                                st.session_state.datos_extraidos = datos_rec
                                inyectar_t2_existente(id_de_lista)
                                st.rerun()
            st.markdown("---")

        st.markdown("---")

        # --- SECCIÓN BORRAR DUPLICADO ---
        with st.expander("🗑️ Eliminar registro duplicado", expanded=False):
            st.warning("⚠️ Esta acción es permanente. Úsala solo para borrar registros duplicados.")
            col_del1, col_del2 = st.columns([3, 1])
            with col_del1:
                id_a_borrar = st.text_input("ID a eliminar (Ej. PED-012):", key="id_borrar")
            with col_del2:
                if st.button("🗑️ Eliminar", use_container_width=True, type="primary"):
                    if id_a_borrar:
                        if eliminar_registro_por_id(id_a_borrar.upper()):
                            st.success(f"✅ Registro {id_a_borrar.upper()} eliminado correctamente.")
                            st.cache_data.clear()
                        else:
                            st.error(f"❌ No se encontró el registro {id_a_borrar.upper()}.")
                    else:
                        st.warning("Ingresa un ID para eliminar.")

        col_b1, col_b2 = st.columns([3, 1])
        with col_b1:
            id_existente = st.text_input(
                "O ingrese el ID_Seguimiento manualmente (Ej. PED-005):")
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

    elif opcion_pedido == "Opción C: Captura Manual (Sin Constancia)":
        st.info("✏️ Modo captura manual activo. Completa los datos del cliente directamente en el formulario de abajo.")
        if not datos:
            # Inicializamos campos vacíos para que el formulario aparezca
            st.session_state.datos_extraidos = {k: "" for k in CAMPOS_SAT}
            st.rerun()

    # --- FORMULARIO DINÁMICO ---
    # Si hay datos (de la opción A o B), mostramos el formulario
    # if datos:
    if datos or opcion_pedido in ["Opción A: Nuevo Cliente (Subir Constancia)", "Opción C: Captura Manual (Sin Constancia)"]:
        st.divider()
        # Buscar contacto si es nuevo cliente y tenemos RFC
        rfc_detectado = datos.get("RFC:", "")
        if rfc_detectado and "Correo Electrónico" not in datos:
            correo_ext, celular_ext = buscar_contacto_externo(rfc_detectado)
            datos["Correo Electrónico"] = correo_ext
            datos["Número Celular"] = celular_ext

        # --- SECCIÓN 1: IDENTIFICACIÓN Y OCUPACIÓN ---
        st.subheader("📋 Documentación y Ocupación")
        col_c1, col_c2, col_c3 = st.columns(3)
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

        st.markdown("""
            <style>
            /* Reducir el tamaño de fuente en selectboxes de Streamlit */
            .stSelectbox div[data-baseweb="select"] {
                font-size: 13px !important;
            }
            .stSelectbox ul[role="listbox"] li {
                font-size: 13px !important;
            }
            </style>
        """, unsafe_allow_html=True)

        # Ocupación en renglón completo
        destino_actual = st.session_state.get("radio_destino_constancia", "datos_pedidos")
        hoja_cat = "ACT_PM" if destino_actual == "PERSONA_MORAL" else "ACT_PF"
        
        with st.spinner("Cargando..."):
            opciones_oc = obtener_catalogo_ocupaciones(hoja_cat)
            
        valor_oc_actual = str(datos.get("OCUPACION", "")).strip()
        if valor_oc_actual in opciones_oc:
            idx_oc = opciones_oc.index(valor_oc_actual)
        else:
            if valor_oc_actual and valor_oc_actual != "None":
                opciones_oc.append(f"{valor_oc_actual} (Detectado)")
                idx_oc = len(opciones_oc) - 1
            else:
                idx_oc = 0
                
        ocupacion_val = st.selectbox("Ocupación:", opciones_oc, index=idx_oc)
        if ocupacion_val.endswith(" (Detectado)"):
            ocupacion_val = ocupacion_val.replace(" (Detectado)", "")

        # --- Fecha de Nacimiento ---
        col_fnac1, col_fnac2, _ = st.columns([2, 2, 2])
        with col_fnac1:
            fecha_nac = st.text_input("📅 Fecha de Nacimiento:", value=datos.get("Fecha_nac", ""), placeholder="DD/MM/AAAA")
        with col_fnac2:
            import datetime
            val_pld1 = datos.get("Fecha PLD 1", "")
            if not val_pld1:
                val_pld1 = datetime.date.today().strftime("%d/%m/%Y")
            fecha_pld1 = st.text_input("📅 Fecha PLD 1:", value=val_pld1, placeholder="DD/MM/AAAA")

        # --- Campos Opcionales para Persona Moral ---
        col_pm1, col_pm2, col_pm3 = st.columns(3)
        with col_pm1:
            fecha_rpp = st.text_input("Fecha de RPP (Opcional):", value=datos.get("Fecha de RPP", ""))
        with col_pm2:
            fecha_poder = st.text_input("Fecha del Poder (Opcional):", value=datos.get("Fecha del Poder", ""))
        with col_pm3:
            tel_emp = st.text_input("Teléfono Emp (Opcional):", value=datos.get("Telefono Emp", ""))

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
            # Pre-seleccionar canales; si no hay ninguno, dejar vacío (NINGUNO)
            seleccionados = [
                opt for opt in fin_opciones if datos.get(opt) == "SÍ"]
            tipo_fin = st.multiselect(
                "Canal de Venta (dejar vacío = NINGUNO):", fin_opciones, default=seleccionados)

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
        with st.expander("🏠 Revisar / Capturar Datos SAT (Dirección y Vialidad)", expanded=(opcion_pedido == "Opción C: Captura Manual (Sin Constancia)")):
            datos_validados = {}
            EXCLUIR_SAT = fin_opciones + [
                "ID_Seguimiento", "EMISION", "FOLIO", "OCUPACION", "Auto", "AÑO",
                "Precio Auto", "Color", "Pago Inicial", "Plazo", "Mensualidades",
                "Monto a Financiar", "GARANTIA EXTENDIDA", "SEGURO", "KIT DE SEGURIDAD",
                "GESTORIA", "PLACAS / TENENCIA", "VERIFICACION", "ACCESORIOS",
                "TOMA DE AUTO", "PRECIO DE TOMA", "GERENTE DE AUTOS SEMINUEVOS",
                "GERENTE DE VENTAS", "Identificaciones", "USO_CFDI", "MET_PAGO",
                "ANTICIPO", "Fecha de RPP", "Fecha del Poder", "Telefono Emp"
            ]

            if opcion_pedido == "Opción C: Captura Manual (Sin Constancia)":
                # Captura libre: mostramos los campos SAT definidos en CAMPOS_SAT
                llaves_sat = CAMPOS_SAT
            else:
                # Modo OCR / edición: solo campos que vienen del OCR
                llaves_sat = [k for k in datos.keys() if k not in EXCLUIR_SAT]

            cols_sat = st.columns(2)
            for i, k in enumerate(llaves_sat):
                with cols_sat[i % 2]:
                    datos_validados[k] = st.text_input(
                        f"{k}", value=datos.get(k, ""))

        # --- AQUÍ VA EL NUEVO FRAGMENTO: SELECCIÓN DE DESTINO ---
        st.divider()
        st.subheader("📍 Selección de Destino de la Información")

        # 1. Agregamos la nueva opción al Radio Button
        destino_hoja = st.radio(
            "¿A qué pestaña deseas enviar esta información?",
            ["datos_pedidos", "REPRESENTANTE_LEGAL", "PERSONA_MORAL"],
            horizontal=True,
            key="radio_destino_constancia"
        )

        id_rep_seleccionado = None
        if destino_hoja == "PERSONA_MORAL":
            st.info("👥 Selecciona el Representante Legal para vincular a esta Empresa:")
            with st.spinner("Cargando representantes..."):
                representantes = obtener_representantes_legales()
            
            if representantes:
                opciones_reps = ["Seleccione un representante..."]
                mapeo_reps = {}
                for rep in representantes:
                    id_rep = str(rep.get("ID_Seguimiento", ""))
                    nombre = str(rep.get("Nombre (s):", ""))
                    ap1 = str(rep.get("Primer Apellido:", ""))
                    ap2 = str(rep.get("Segundo Apellido:", ""))
                    rfc = str(rep.get("RFC:", ""))
                    
                    if id_rep:
                        texto_mostrar = f"{id_rep} - {nombre} {ap1} {ap2} - RFC: {rfc}".strip()
                        opciones_reps.append(texto_mostrar)
                        mapeo_reps[texto_mostrar] = id_rep
                        
                seleccion_rep = st.selectbox("Representante Legal (Opcional):", opciones_reps)
                if seleccion_rep != "Seleccione un representante...":
                    id_rep_seleccionado = mapeo_reps[seleccion_rep]
            else:
                st.warning("No se encontraron representantes legales.")

        # --- BOTÓN DE CIERRE ---
        # --- BOTÓN DE CIERRE (ESTRUCTURA FINAL REFORZADA) ---
        # --- BOTÓN DE CIERRE (VERSIÓN FINAL OPTIMIZADA Y SIN DUPLICADOS) ---
        # --- BOTÓN ACTUALIZAR (modo forzado para registros existentes) ---
        id_activo = st.session_state.get("datos_extraidos", {}).get("ID_Seguimiento", "")
        if id_activo and destino_hoja == "datos_pedidos":
            st.info(f"📂 Registro activo: **{id_activo}** — Usa 'Actualizar' para guardar cambios sin crear duplicado.")
            col_btn1, col_btn2 = st.columns(2)
            btn_confirmar = col_btn1.button(f"✅ Confirmar e Inyectar en {destino_hoja}", use_container_width=True)
            btn_actualizar = col_btn2.button(f"🔄 Actualizar registro {id_activo}", use_container_width=True, type="primary")
        else:
            col_btn1, _ = st.columns([1, 1])
            btn_confirmar = col_btn1.button(f"✅ Confirmar e Inyectar en {destino_hoja}", use_container_width=True)
            btn_actualizar = False

        if btn_confirmar or btn_actualizar:
            # AQUÍ VA EL PRIMER BLOQUE (La Validación)
            if destino_hoja == "datos_pedidos" and ident_sel == "SELECCIONE UNA OPCIÓN":
                st.error(
                    "❌ Para registros de Personas Físicas es obligatorio seleccionar un Tipo de Identificación.")

            else:
                datos_del_ocr = st.session_state.get("datos_extraidos", {})
                id_a_editar = datos_del_ocr.get("ID_Seguimiento")

                with st.spinner(f"Guardando en {destino_hoja}..."):
                    # 1. Consolidación total de datos
                    datos_finales = {**datos_del_ocr, **datos_validados}
                    datos_finales.update({
                        "Identificaciones": ident_sel, "EMISION": emis_sel, "FOLIO": folio_val,
                        "OCUPACION": ocupacion_val, "Auto": auto_val, "AÑO": año_val,
                        "Precio Auto": precio_val, "Color": color_val, "Pago Inicial": pago_ini_val,
                        "Plazo": plazo_val, "Mensualidades": mensualidad_val, "Monto a Financiar": monto_fin_val,
                        # Canal de Venta: solo escribe SÍ si fue seleccionado; si no, vacío
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
                        "GERENTE DE AUTOS SEMINUEVOS": gerente_semi,
                        "GERENTE DE VENTAS": gerente_ventas,
                        "USO_CFDI": uso_cfdi,
                        "MET_PAGO": met_pago,
                        "ANTICIPO": anticipo,
                        "Fecha de RPP": fecha_rpp,
                        "Fecha del Poder": fecha_poder,
                        "Telefono Emp": tel_emp,
                        "Fecha_nac": fecha_nac,
                        "Fecha PLD 1": fecha_pld1
                    })
                    # Si es modo Actualizar, forzamos el ID para que siempre edite
                    if btn_actualizar and id_activo:
                        id_a_editar = id_activo

                    # --- AQUÍ EMPIEZA EL BLOQUE CORREGIDO ---

                try:
                    # 1. RUTA PARA PERSONA FÍSICA (Base General)
                    if destino_hoja == "datos_pedidos":
                        id_gen = guardar_pedido_y_actualizar_t2(
                            datos_finales, id_actualizar=id_a_editar)
                        if id_gen:
                            actualizar_ultimo_registro_hoja("Pedido", id_gen)
                            actualizar_ultimo_registro_hoja(
                                "pedido_stellantis", id_gen)
                            st.success(f"✅ Registro Físico Exitoso: {id_gen}")
                            st.balloons()
                        else:
                            st.error("🛑 Error al guardar en la base general.")

                    # 2. RUTA PARA PERSONA MORAL (Base Independiente)
                    elif destino_hoja == "PERSONA_MORAL":
                        # --- GENERACIÓN DE ID ESPECÍFICO ---
                        if not id_a_editar:
                            id_gen = generar_id_especifico(
                                "PERSONA_MORAL", "PM")
                            datos_finales["ID_Seguimiento"] = id_gen
                        else:
                            id_gen = id_a_editar

                        datos_para_sheets = {
                            k: v for k, v in datos_finales.items() if str(v).strip() != ""}
                        exito = inyectar_datos_generico(
                            datos_para_sheets, "PERSONA_MORAL")

                        if exito:
                            actualizar_ultimo_registro_hoja(
                                "pedido_stellantis_pm", id_gen)
                                
                            if id_rep_seleccionado:
                                actualizar_representante_en_pm_stellantis(id_rep_seleccionado)
                                
                            st.success(
                                f"🏢 Registro de Empresa Guardado con ID: {id_gen}")
                            st.balloons()
                        else:
                            st.error(
                                "❌ Error al inyectar en la pestaña PERSONA_MORAL.")

                    # 3. RUTA PARA REPRESENTANTE LEGAL (Base Independiente)
                    elif destino_hoja == "REPRESENTANTE_LEGAL":
                        # --- GENERACIÓN DE ID ESPECÍFICO ---
                        if not id_a_editar:
                            id_gen = generar_id_especifico(
                                "REPRESENTANTE_LEGAL", "RL")
                            datos_finales["ID_Seguimiento"] = id_gen
                        else:
                            id_gen = id_a_editar

                        datos_para_sheets = {
                            k: v for k, v in datos_finales.items() if str(v).strip() != ""}
                        exito = inyectar_datos_generico(
                            datos_para_sheets, "REPRESENTANTE_LEGAL")

                        if exito:
                            actualizar_campo_pld_representante(id_gen)
                            st.success(
                                f"⚖️ Registro de Representante Guardado con ID: {id_gen}")
                            st.balloons()
                        else:
                            st.error(
                                "❌ Error al inyectar en la pestaña REPRESENTANTE_LEGAL.")

                except Exception as e:
                    st.error(
                        f"🛑 Ocurrió un error inesperado durante la inyección: {e}")

        # --- AQUÍ COLOCAMOS EL BOTÓN DE LIMPIAR (AL FINAL) ---
        st.write("---")  # Una línea divisora para separar del botón de guardado
        if st.button("♻️ Limpiar Formulario / Nuevo Registro", use_container_width=True):
            st.session_state.datos_extraidos = {}
            st.rerun()

        st.divider()
        st.subheader("🖨️ Formatos para Impresión")

        # Tus botones actuales (No los toques si ya funcionan)
        cp1, cp2 = st.columns(2)
        with cp1:
            st.link_button("📄 Imprimir Pedido Nissan", obtener_url_impresion(
                "Pedido"), use_container_width=True)
            st.link_button("🚗 Imprimir Pedido EMPRESA Nissan (PM)", obtener_url_impresion(
                "pedido_pm_nissan"), use_container_width=True, type="primary")
        with cp2:
            st.link_button("📄 Imprimir Pedido Stellantis", obtener_url_impresion(
                "pedido_stellantis"), use_container_width=True)
            st.link_button("🚗 Imprimir Pedido EMPRESA Stellantis (PM)", obtener_url_impresion(
                "pedido_stellantis_pm"), use_container_width=True, type="primary")

        # --- PAPELERIA NISSAN ---
        st.write("---")
        with st.expander("📁 PAPELERIA NISSAN", expanded=False):
            st.subheader("📄 Formatos PLD (Individuales)")
            c_pld1, c_pld2, c_pld3 = st.columns(3)
            with c_pld1:
                st.link_button("📄 PLD 1", obtener_url_pld(
                    "PLD_1"), use_container_width=True)
            with c_pld2:
                st.link_button("📄 PLD 2", obtener_url_pld(
                    "PLD_2"), use_container_width=True)
            with c_pld3:
                st.link_button("📄 PLD 3", obtener_url_pld(
                    "PLD_3"), use_container_width=True)

            st.divider()

            st.subheader("🏢 Formatos para la Empresa (Persona Moral)")
            c_pld_m1, c_pld_m2, c_pld_m3 = st.columns(3)
            c_pld_m1.link_button("📋 PM 1", obtener_url_pld(
                "PLD_PM1"), use_container_width=True)
            c_pld_m2.link_button("📋 PM 2", obtener_url_pld(
                "PLD_PM2"), use_container_width=True)
            c_pld_m3.link_button("📋 PM 3", obtener_url_pld(
                "PLD_PM3"), use_container_width=True)

            st.divider()

            st.subheader("⚖️ Formatos para el Representante Legal")
            c_rl1, c_rl2, c_rl3 = st.columns(3)
            c_rl1.link_button("👤 PLD RL 1", obtener_url_pld(
                "PLD_1_RL"), use_container_width=True)
            c_rl2.link_button("👤 PLD RL 2", obtener_url_pld(
                "PLD_2_RL"), use_container_width=True)
            c_rl3.link_button("👤 PLD RL 3", obtener_url_pld(
                "PLD_3_RL"), use_container_width=True)


        st.write("---")  # Tu línea divisoria actual

# --- APARTADO DE IMPRESIONES STELLANTIS ---
    with st.expander("📂 Constancias e Impresiones Stellantis (PF / PM / RL)"):

        # SECCIÓN PERSONA FÍSICA
        st.subheader("👤 Persona Física - Stellantis")
        col_pf1, col_pf2 = st.columns(2)
        with col_pf1:
            st.link_button("📄 Imprimir Parte 1 (PF)", obtener_url_pld(
                "PF_STELLANTIS_1"), use_container_width=True)
        with col_pf2:
            st.link_button("📄 Imprimir Parte 2 (PF)", obtener_url_pld(
                "PF_STELLANTIS_2"), use_container_width=True)

        st.divider()

        # SECCIÓN PERSONA MORAL
        st.subheader("🏢 Persona Moral - Stellantis")
        col_pm1, col_pm2 = st.columns(2)
        with col_pm1:
            st.link_button("📄 Imprimir Parte 1 (PM)", obtener_url_pld(
                "PM_STELLANTIS_1"), use_container_width=True)
        with col_pm2:
            st.link_button("📄 Imprimir Parte 2 (PM)", obtener_url_pld(
                "PM_STELLANTIS_2"), use_container_width=True)

        st.divider()

        # SECCIÓN REPRESENTANTE LEGAL
        st.subheader("⚖️ Representante Legal - Stellantis")
        col_rl1, col_rl2 = st.columns(2)
        with col_rl1:
            st.link_button("👤 Imprimir Parte 1 (RL)", obtener_url_pld(
                "PF_STELLANTIS_RL_1"), use_container_width=True)
        with col_rl2:
            st.link_button("👤 Imprimir Parte 2 (RL)", obtener_url_pld(
                "PF_STELLANTIS_RL_2"), use_container_width=True)

        # El botón solo aparece si ya subiste la constancia y el OCR leyó los datos
        # --- SECCIÓN: AVISO DE PRIVACIDAD STELLA MOTORS ---
        st.write("---")

        # Usamos 'datos_extraidos' porque ahí se guarda tanto lo del OCR como lo de Sheets
        if st.session_state.get('datos_extraidos'):
            if st.button("📝 Generar Aviso de Privacidad (PDF)", use_container_width=True):
                # Llamamos a la función usando la memoria actual
                pdf_buffer, nombre_archivo = generar_pdf_aviso_privacidad(
                    st.session_state.datos_extraidos)

                st.download_button(
                    label=f"⬇️ Descargar {nombre_archivo}",
                    data=pdf_buffer,
                    file_name=nombre_archivo,
                    mime="application/pdf",
                    use_container_width=True
                )
        else:
            st.info(
                "ℹ️ Sube una Constancia o carga un ID para habilitar el Aviso de Privacidad.")
