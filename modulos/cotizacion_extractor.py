"""
cotizacion_extractor.py - Extractor 100% local con PyMuPDF (0 Tokens, Gratis y Ultra Rápido)
Inspirado en la lógica de extracción de tablas/coordenadas de extractor_ia, integrado de forma
totalmente independiente dentro de Gestor_Creditos.

REGLAS DE NEGOCIO ESTRICTAS:
1. Exclusivo para cotizaciones de crédito (Financiera Propia: Stellantis Financial / Inbursa, CrediNissan, etc.).
2. Trabaja 100% con PyMuPDF (sin consumir tokens de Gemini ni depender de API Keys).
3. NO toca ni sobreescribe ningún campo de la Constancia de Situación Fiscal (SAT).
4. NO llena el campo 'SEGURO' (cuando es crédito por financiera de casa no se llena en el pedido).
5. Llena únicamente los campos de la unidad y financiamiento, dejándolos 100% editables en la interfaz:
   - Auto (Modelo / Versión)
   - AÑO (Año modelo)
   - Precio Auto (Precio Lista / Precio Vehículo)
   - Pago Inicial (Enganche del vehículo)
   - Monto a Financiar (Financiado)
   - Plazo (12, 18, 24, 36, 48, 60, 72)
   - Mensualidades (Pago mensual)
   - FINANCIERA PROPIA ("SÍ")
   - ANTICIPO (Anticipo total)
"""

import io
import re


PLAZOS_VALIDOS = ["12", "18", "24", "36", "48", "60", "72"]

# Campos exclusivos que pueden inyectarse en st.session_state.datos_extraidos desde la cotización
CAMPOS_PERMITIDOS_COTIZACION = {
    "Auto",
    "AÑO",
    "Precio Auto",
    "Pago Inicial",
    "Monto a Financiar",
    "Plazo",
    "Mensualidades",
    "FINANCIERA PROPIA",
    "ANTICIPO",
}


def _limpiar_monto(valor) -> float:
    """Convierte un string de moneda (ej. '$537,500.00') o número a float."""
    if valor is None:
        return 0.0
    if isinstance(valor, (int, float)):
        return round(float(valor), 2)
    s = str(valor).strip()
    if not s:
        return 0.0
    m = re.search(r"[\d,]+(?:\.\d+)?", s.replace(" ", ""))
    if not m:
        return 0.0
    try:
        return round(float(m.group(0).replace(",", "")), 2)
    except ValueError:
        return 0.0


def _normalizar_plazo(valor) -> str:
    """Normaliza el plazo extraído (ej. '12 Pagos', '36 meses', 24) a los valores del selectbox."""
    if valor is None:
        return "12"
    s = str(valor).strip()
    m = re.search(r"\b(12|18|24|36|48|60|72)\b", s)
    if m:
        return m.group(1)
    m_any = re.search(r"\d+", s)
    if m_any:
        num_str = m_any.group(0)
        if num_str in PLAZOS_VALIDOS:
            return num_str
    return "12"


def _agrupar_items_en_filas(items: list, y_descendente: bool = False, tol_y: float = 4.5) -> list:
    """
    Agrupa una lista de tuplas (x, y, texto) en líneas horizontales ordenadas verticalmente
    y de izquierda a derecha (por x).
    - Si y_descendente=False (ej. fitz top-down), ordena de menor Y a mayor Y.
    - Si y_descendente=True (ej. pypdf bottom-up), ordena de mayor Y a menor Y.
    """
    if not items:
        return []

    signo = -1.0 if y_descendente else 1.0
    items_ordenados = sorted(items, key=lambda it: (signo * round(it[1] / 3.5) * 3.5, it[0]))

    filas = []
    fila_actual = []
    y_actual = None

    for x, y, texto in items_ordenados:
        if y_actual is None or abs(y - y_actual) <= tol_y:
            fila_actual.append((x, texto))
            if y_actual is None:
                y_actual = y
        else:
            fila_actual.sort(key=lambda item: item[0])
            filas.append(" ".join(t for _, t in fila_actual))
            fila_actual = [(x, texto)]
            y_actual = y

    if fila_actual:
        fila_actual.sort(key=lambda item: item[0])
        filas.append(" ".join(t for _, t in fila_actual))

    return filas


def extraer_lineas_ordenadas_pdf(file_bytes: bytes) -> str:
    """
    Extrae el texto del PDF reconstruyendo el orden visual por coordenadas (Y, X)
    y separando columnas izquierda/derecha en el encabezado para evitar mezclar
    datos del cliente con datos del vehículo.
    Utiliza PyMuPDF (fitz) como motor principal (y pypdf como respaldo).
    """
    lineas_finales = []

    # 1. Motor principal: PyMuPDF (fitz)
    try:
        import fitz
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        num_paginas = min(len(doc), 2)
        for p_idx in range(num_paginas):
            page = doc[p_idx]
            palabras = page.get_text("words")  # (x0, y0, x1, y1, word, block_no, line_no, word_no)
            if not palabras:
                continue

            items = [(float(w[0]), float(w[1]), str(w[4]).strip()) for w in palabras if str(w[4]).strip()]

            # En página 1, detectar la coordenada Y de "CONDICIONES" para separar columnas arriba de esa línea
            y_condiciones = None
            for x, y, t in items:
                if "CONDICIONES" in t.upper():
                    y_condiciones = y
                    break

            lineas_finales.append(f"--- PÁGINA {p_idx + 1} ---")
            if y_condiciones is not None and p_idx == 0:
                encabezado_izq = [(x, y, t) for (x, y, t) in items if y < y_condiciones - 2 and x < 285]
                encabezado_der = [(x, y, t) for (x, y, t) in items if y < y_condiciones - 2 and x >= 285]
                cuerpo_tabla = [(x, y, t) for (x, y, t) in items if y >= y_condiciones - 2]

                lineas_finales.extend(_agrupar_items_en_filas(encabezado_izq, y_descendente=False))
                lineas_finales.extend(_agrupar_items_en_filas(encabezado_der, y_descendente=False))
                lineas_finales.extend(_agrupar_items_en_filas(cuerpo_tabla, y_descendente=False))
            else:
                lineas_finales.extend(_agrupar_items_en_filas(items, y_descendente=False))

        doc.close()
        if lineas_finales:
            return "\n".join(lineas_finales)
    except Exception:
        pass

    # 2. Respaldo con pypdf reconstruyendo coordenadas (cm + tm)
    try:
        import pypdf
        reader = pypdf.PdfReader(io.BytesIO(file_bytes))
        num_paginas = min(len(reader.pages), 2)
        for p_idx in range(num_paginas):
            page = reader.pages[p_idx]
            items = []

            def _visitor(text, cm, tm, fd, fs):
                if not text or not text.strip():
                    return
                t_clean = text.strip()
                if t_clean.count("\n") > 5:
                    return
                has_cm_offset = (abs(cm[4]) > 0.01 or abs(cm[5]) > 0.01)
                if has_cm_offset:
                    x, y = float(cm[4]), float(cm[5])
                elif float(tm[5]) > 80.0:
                    x, y = float(tm[4]), float(tm[5])
                else:
                    return
                items.append((x, y, t_clean.replace("\n", " | ")))

            page.extract_text(visitor_text=_visitor)
            if not items:
                raw_txt = page.extract_text() or ""
                if raw_txt.strip():
                    lineas_finales.append(f"--- PÁGINA {p_idx + 1} ---")
                    lineas_finales.append(raw_txt)
                continue

            y_condiciones = None
            for x, y, t in items:
                if "CONDICIONES" in t.upper():
                    y_condiciones = y
                    break

            lineas_finales.append(f"--- PÁGINA {p_idx + 1} ---")
            if y_condiciones is not None and p_idx == 0:
                encabezado_izq = [(x, y, t) for (x, y, t) in items if y > y_condiciones + 2 and x < 285]
                encabezado_der = [(x, y, t) for (x, y, t) in items if y > y_condiciones + 2 and x >= 285]
                cuerpo_tabla = [(x, y, t) for (x, y, t) in items if y <= y_condiciones + 2]

                lineas_finales.extend(_agrupar_items_en_filas(encabezado_izq, y_descendente=True))
                lineas_finales.extend(_agrupar_items_en_filas(encabezado_der, y_descendente=True))
                lineas_finales.extend(_agrupar_items_en_filas(cuerpo_tabla, y_descendente=True))
            else:
                lineas_finales.extend(_agrupar_items_en_filas(items, y_descendente=True))

        if lineas_finales:
            return "\n".join(lineas_finales)
    except Exception:
        pass

    return ""


def extraer_cotizacion_local(texto_estructurado: str) -> dict:
    """
    Parser determinístico de alta precisión sobre el texto ordenado por coordenadas con PyMuPDF.
    Extrae los datos financieros y de la unidad de la cotización con 0 tokens.
    """
    resultado = {
        "Auto": "",
        "AÑO": "",
        "Precio Auto": 0.0,
        "Pago Inicial": 0.0,
        "Monto a Financiar": 0.0,
        "Plazo": "12",
        "Mensualidades": 0.0,
        "FINANCIERA PROPIA": "SÍ",
        "ANTICIPO": "",
        "_meta": {
            "folio_cotizacion": "",
            "marca": "",
            "plan": "",
            "tasa_interes": "",
            "monto_financiado_vehiculo": 0.0,
            "monto_financiado_total": 0.0,
            "anticipo_vehiculo": 0.0,
            "anticipo_total": 0.0,
            "bono_descuento": 0.0,
            "anticipo_sin_bono": 0.0,
            "metodo_extraccion": "PyMuPDF Local (0 Tokens)",
        }
    }

    if not texto_estructurado:
        return resultado

    lineas = [l.strip() for l in texto_estructurado.splitlines() if l.strip()]

    for i, linea in enumerate(lineas):
        linea_upper = linea.upper()

        # 1. FOLIO DE COTIZACIÓN
        if "FOLIO:" in linea_upper and not resultado["_meta"]["folio_cotizacion"]:
            m_folio = re.search(r"FOLIO:\s*(\S+)", linea, re.IGNORECASE)
            if m_folio:
                resultado["_meta"]["folio_cotizacion"] = m_folio.group(1).strip()

        # 2. MARCA
        if "MARCA:" in linea_upper and not resultado["_meta"]["marca"]:
            m_marca = re.search(r"MARCA:\s*(.+)$", linea, re.IGNORECASE)
            if m_marca:
                resultado["_meta"]["marca"] = m_marca.group(1).strip()

        # 3. VEHÍCULO / VERSIÓN (Auto)
        if ("VEHÍCULO/VERSIÓN" in linea_upper or "VEHICULO/VERSION" in linea_upper or ("VEH" in linea_upper and "VERSI" in linea_upper)) and not resultado["Auto"]:
            m_veh = re.search(r"VERSI[^:]*:\s*(.+)$", linea, re.IGNORECASE)
            partes_veh = []
            if m_veh and m_veh.group(1).strip():
                partes_veh.append(m_veh.group(1).strip())
            if i + 1 < len(lineas):
                sig = lineas[i + 1].strip()
                sig_up = sig.upper()
                if not any(sig_up.startswith(etq) for etq in ("MODELO:", "FECHA", "VIGENCIA:", "PLAN:", "PRODUCTO:", "CONDICIONES")):
                    partes_veh.append(sig)
            if partes_veh:
                resultado["Auto"] = " ".join(partes_veh).strip()

        # 4. MODELO / AÑO
        if "MODELO:" in linea_upper and not resultado["AÑO"]:
            m_mod = re.search(r"MODELO:\s*(20\d{2})\b", linea, re.IGNORECASE)
            if m_mod:
                resultado["AÑO"] = m_mod.group(1)
            elif i + 1 < len(lineas):
                m_mod_sig = re.search(r"\b(20\d{2})\b", lineas[i + 1])
                if m_mod_sig:
                    resultado["AÑO"] = m_mod_sig.group(1)

        # 5. PLAN
        if "PLAN:" in linea_upper and not resultado["_meta"]["plan"]:
            m_plan = re.search(r"PLAN:\s*(.+)$", linea, re.IGNORECASE)
            if m_plan and m_plan.group(1).strip():
                resultado["_meta"]["plan"] = m_plan.group(1).strip()
            elif i + 1 < len(lineas):
                sig = lineas[i + 1].strip()
                if not sig.upper().startswith("PRODUCTO:"):
                    resultado["_meta"]["plan"] = sig

        # 6. FILA PRECIO VEHÍCULO / PRECIO TOTAL
        # Ej: "Precio Vehículo: $537,500.00 80.00% $430,000.00 $107,500.00"
        if ("PRECIO VEH" in linea_upper or "PRECIO TOTAL" in linea_upper) and resultado["Precio Auto"] == 0.0:
            montos = re.findall(r"\$\s*([\d,]+\.\d{2})", linea)
            if len(montos) >= 3:
                precio_v = _limpiar_monto(montos[0])
                enganche_v = _limpiar_monto(montos[1])
                financiado_v = _limpiar_monto(montos[2])
                resultado["Precio Auto"] = precio_v
                resultado["Pago Inicial"] = enganche_v
                resultado["_meta"]["anticipo_vehiculo"] = enganche_v
                resultado["_meta"]["monto_financiado_vehiculo"] = financiado_v
                if resultado["Monto a Financiar"] == 0.0:
                    resultado["Monto a Financiar"] = financiado_v
            elif len(montos) == 1:
                resultado["Precio Auto"] = _limpiar_monto(montos[0])

        # 7. FILA TOTAL DE TABLA CONDICIONES
        # Ej: "Total: $459,355.61 $107,942.56"
        if re.match(r"^TOTAL:\s*\$", linea_upper):
            montos_tot = re.findall(r"\$\s*([\d,]+\.\d{2})", linea)
            if len(montos_tot) == 2:
                ant_tot = _limpiar_monto(montos_tot[0])
                fin_tot = _limpiar_monto(montos_tot[1])
                resultado["_meta"]["anticipo_total"] = ant_tot
                resultado["_meta"]["monto_financiado_total"] = fin_tot
                resultado["Monto a Financiar"] = fin_tot
                if resultado["_meta"]["anticipo_sin_bono"] == 0.0:
                    resultado["ANTICIPO"] = f"{ant_tot:,.2f}"

        # 7b. BONO DEL DESCUENTO (cuando aplica bono en la cotización)
        # Ej: "Bono del Descuento: $-75,000.00"
        if ("BONO DEL DESCUENTO" in linea_upper or "BONO DE DESCUENTO" in linea_upper) and "ANTICIPO SIN BONO" not in linea_upper:
            m_bono = re.search(r"-?\s*([\d,]+\.\d{2})", linea)
            if m_bono:
                resultado["_meta"]["bono_descuento"] = _limpiar_monto(m_bono.group(1))

        # 7c. ANTICIPO SIN BONO DEL DESCUENTO (Enganche real cuando se ofrece bono)
        # Ej: "Anticipo sin bono del descuento: $103,680.67"
        if "ANTICIPO SIN BONO" in linea_upper:
            m_ant_sb = re.search(r"\$?\s*([\d,]+\.\d{2})", linea)
            if m_ant_sb:
                ant_sin_bono = _limpiar_monto(m_ant_sb.group(1))
                if ant_sin_bono > 0:
                    resultado["_meta"]["anticipo_sin_bono"] = ant_sin_bono
                    resultado["Pago Inicial"] = ant_sin_bono
                    resultado["ANTICIPO"] = f"{ant_sin_bono:,.2f}"

        # 8. PLAZO
        if linea_upper.startswith("PLAZO:"):
            resultado["Plazo"] = _normalizar_plazo(linea)

        # 9. TASA DE INTERÉS
        if "TASA DE INTER" in linea_upper and not resultado["_meta"]["tasa_interes"]:
            m_tasa = re.search(r"([\d.]+\s*%)", linea)
            if m_tasa:
                resultado["_meta"]["tasa_interes"] = m_tasa.group(1)

        # 10. RESUMEN DE MENSUALIDAD
        # Ej: "12 Pagos Mensuales c/u de: $9,835.66 (Pagos Vencidos)."
        # Ej: "60 Pagos Mensuales c/u de 8,814.92 (no incluye seguro)."
        if "PAGOS MENSUALES" in linea_upper and resultado["Mensualidades"] == 0.0:
            m_plazo_res = re.search(r"(\d+)\s+PAGOS\s+MENSUALES", linea_upper)
            if m_plazo_res:
                resultado["Plazo"] = _normalizar_plazo(m_plazo_res.group(1))
            m_mens = re.search(r"(?:DE:?|\$)\s*\$?\s*([\d,]+\.\d{2})", linea_upper)
            if m_mens:
                resultado["Mensualidades"] = _limpiar_monto(m_mens.group(1))

    if not resultado["ANTICIPO"] and resultado["Pago Inicial"] > 0:
        resultado["ANTICIPO"] = f"{resultado['Pago Inicial']:,.2f}"

    return resultado


def extraer_datos_cotizacion(file_bytes: bytes) -> dict:
    """
    Función principal que procesa el PDF de la cotización de crédito 100% con PyMuPDF (0 tokens).
    1. Extrae y alinea el texto por coordenadas visuales con PyMuPDF (fitz).
    2. Ejecuta el extractor local por coordenadas.
    3. Devuelve únicamente los campos permitidos para la unidad y el financiamiento,
       sin tocar jamás los campos del SAT ni el campo SEGURO.
    """
    texto_estructurado = extraer_lineas_ordenadas_pdf(file_bytes)
    return extraer_cotizacion_local(texto_estructurado)


def aplicar_cotizacion_a_datos(datos_actuales: dict, datos_cotizacion: dict) -> dict:
    """
    Aplica ÚNICAMENTE los campos permitidos de la cotización sobre el diccionario
    de datos actuales (`st.session_state.datos_extraidos`), garantizando que:
    - Los datos de la Constancia de Situación Fiscal (SAT) queden intactos.
    - El campo 'SEGURO' NO se llene ni modifique.
    - El canal 'FINANCIERA PROPIA' quede marcado como 'SÍ'.
    """
    nuevo_dict = dict(datos_actuales) if datos_actuales else {}

    for campo in CAMPOS_PERMITIDOS_COTIZACION:
        if campo in datos_cotizacion:
            valor = datos_cotizacion[campo]
            if valor is not None and str(valor).strip() != "":
                nuevo_dict[campo] = valor

    # Asegurar que FINANCIERA PROPIA esté activo para el multiselect de app.py
    nuevo_dict["FINANCIERA PROPIA"] = "SÍ"

    # Regla explícita: cuando es crédito por financiera de casa, SEGURO no se llena desde la cotización
    # No tocamos ni inyectamos "SEGURO"

    return nuevo_dict
