"""
ocr_processor.py - Extracción de datos de Constancias de Situación Fiscal
Mejoras:
  - Lectura multi-página completa (no solo página 1)
  - Búsqueda de todas las ocurrencias de cada etiqueta en el PDF
  - Normalización de acentos para búsqueda robusta (Código = Codigo)
  - Detección de valores pegados a la etiqueta (Código Postal:56900)
  - Búsqueda por líneas de texto como fallback cuando falla la búsqueda por palabras
  - Respaldo automático por QR oficial del SAT (OpenCV + Validador QR SAT) para PDFs escaneados
    (imágenes dentro de PDF, páginas invertidas o archivos JPG/PNG)
"""
import re
import ssl
import html as html_lib
import unicodedata
import urllib.request
import fitz


def _normalizar(texto: str) -> str:
    """Elimina acentos y pasa a mayúsculas para comparación robusta."""
    texto = str(texto or "").upper()
    nfkd = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def extraer_fecha_nac_de_rfc_o_curp(rfc: str = "", curp: str = "") -> str:
    """
    Extrae la fecha de nacimiento en formato DD/MM/YYYY a partir de los 6 dígitos
    (AAMMDD) de un CURP o RFC de Persona Física.
    """
    for cand in (str(curp).strip().upper(), str(rfc).strip().upper()):
        m = re.match(r"^[A-ZÑ&]{4}(\d{2})(\d{2})(\d{2})", cand)
        if m:
            yy, mm, dd = int(m.group(1)), int(m.group(2)), int(m.group(3))
            if 1 <= mm <= 12 and 1 <= dd <= 31:
                anio = 1900 + yy if yy >= 25 else 2000 + yy
                return f"{dd:02d}/{mm:02d}/{anio:04d}"
    return ""


def _formatear_fecha_sat(fecha_str: str) -> str:
    """Convierte fechas como '14-05-1993' a '14/05/1993'."""
    if not fecha_str:
        return ""
    s = str(fecha_str).strip()
    m = re.match(r"^(\d{2})[-/](\d{2})[-/](\d{4})$", s)
    if m:
        return f"{m.group(1)}/{m.group(2)}/{m.group(3)}"
    return s


def _extraer_qrs_de_imagen_bgr(img_bgr, detector):
    """Intenta detectar URLs QR en una imagen BGR usando varios recortes y preprocesamientos."""
    import cv2

    urls = []
    h, w = img_bgr.shape[:2]
    # Probar imagen completa y cuadrante superior izquierdo (donde viene el QR de la Cédula)
    regiones = [
        img_bgr,
        img_bgr[0:int(h * 0.55), 0:int(w * 0.55)],
        img_bgr[int(h * 0.45):h, int(w * 0.45):w],
    ]
    for reg in regiones:
        if reg.size == 0:
            continue
        for candidato in (reg, cv2.cvtColor(reg, cv2.COLOR_BGR2GRAY)):
            try:
                ok, decoded_info, _, _ = detector.detectAndDecodeMulti(candidato)
                if ok and decoded_info:
                    for val in decoded_info:
                        if val and val.strip() and val.strip() not in urls:
                            urls.append(val.strip())
            except Exception:
                pass
            try:
                val, _, _ = detector.detectAndDecode(candidato)
                if val and val.strip() and val.strip() not in urls:
                    urls.append(val.strip())
            except Exception:
                pass
    return urls


def _detectar_urls_qr_sat(file_bytes: bytes, is_pdf: bool = True) -> list:
    """Detecta URLs del validador QR del SAT desde un PDF escaneado o imagen JPG/PNG."""
    try:
        import cv2
        import numpy as np
    except ImportError:
        return []

    detector = cv2.QRCodeDetector()
    urls_encontradas = []

    if is_pdf:
        try:
            doc = fitz.open(stream=file_bytes, filetype="pdf")
        except Exception:
            return []
        try:
            for page in doc:
                for scale in (2.0, 3.0, 1.5):
                    pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale))
                    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
                    if pix.n == 4:
                        img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
                    elif pix.n == 1:
                        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
                    nuevas = _extraer_qrs_de_imagen_bgr(img, detector)
                    for u in nuevas:
                        if u not in urls_encontradas:
                            urls_encontradas.append(u)
                    # Si ya encontramos el QR de Cédula (D1=10), no necesitamos más escalas en esta página
                    if any("D1=10" in u for u in nuevas):
                        break
        finally:
            doc.close()
    else:
        try:
            arr = np.frombuffer(file_bytes, dtype=np.uint8)
            img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if img is not None:
                urls_encontradas.extend(_extraer_qrs_de_imagen_bgr(img, detector))
        except Exception:
            pass

    # Priorizar URLs con D1=10 (Cédula completa con identidad + domicilio) antes que D1=26 (Sello)
    urls_encontradas.sort(key=lambda u: 0 if "D1=10" in u else 1)
    return urls_encontradas


def _consultar_validador_qr_sat(urls_qr: list) -> dict:
    """
    Consulta la página oficial del Validador QR del SAT (siat.sat.gob.mx)
    y devuelve el diccionario de campos para Gestor de Créditos.
    """
    if not urls_qr:
        return {}

    ctx = ssl.create_default_context()
    try:
        ctx.set_ciphers("DEFAULT:@SECLEVEL=1")
    except Exception:
        pass
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    pares = {}
    rfc_detectado = ""

    for url in urls_qr:
        if "sat.gob.mx" not in url:
            continue
        # Extraer RFC desde parámetro D3=<idCIF>_<RFC>
        m_d3 = re.search(r"D3=[^&_]+_([A-ZÑ&0-9]{12,13})", url, re.I)
        if m_d3 and not rfc_detectado:
            rfc_detectado = m_d3.group(1).upper()

        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            )
            raw_html = urllib.request.urlopen(req, context=ctx, timeout=10).read().decode("utf-8", "ignore")
        except Exception:
            continue

        if not rfc_detectado:
            m_rfc = re.search(r"El RFC:\s*([A-ZÑ&0-9]{12,13})", raw_html, re.I)
            if m_rfc:
                rfc_detectado = m_rfc.group(1).upper()

        celdas = []
        for m in re.finditer(r"<td[^>]*>(.*?)</td>", raw_html, re.S | re.I):
            limpio = re.sub(r"<[^>]+>", " ", m.group(1))
            limpio = html_lib.unescape(limpio)
            limpio = re.sub(r"\s+", " ", limpio).strip()
            celdas.append(limpio)

        for idx in range(len(celdas) - 1):
            c_actual = celdas[idx]
            if c_actual.endswith(":"):
                clave_norm = _normalizar(c_actual).rstrip(":").strip()
                val_sig = celdas[idx + 1]
                if not val_sig.endswith(":") and clave_norm not in pares:
                    pares[clave_norm] = val_sig.strip()

    if not pares and not rfc_detectado:
        return {}

    rfc_final = rfc_detectado or pares.get("RFC", "")
    curp_final = pares.get("CURP", "")
    fnac_sat = _formatear_fecha_sat(pares.get("FECHA NACIMIENTO", ""))
    if not fnac_sat:
        fnac_sat = extraer_fecha_nac_de_rfc_o_curp(rfc_final, curp_final)

    municipio = pares.get("MUNICIPIO O DELEGACION", "")
    localidad = pares.get("LOCALIDAD", "") or municipio

    return {
        # 1. Identidad Persona Física
        "RFC:":            rfc_final,
        "CURP:":           curp_final,
        "Nombre (s):":     pares.get("NOMBRE", ""),
        "Primer Apellido:":  pares.get("APELLIDO PATERNO", ""),
        "Segundo Apellido:": pares.get("APELLIDO MATERNO", ""),
        "Fecha_nac":       fnac_sat,

        # 2. Identidad Persona Moral
        "Denominación/Razón Social:": pares.get("DENOMINACION O RAZON SOCIAL", ""),
        "Régimen Capital:":           pares.get("REGIMEN DE CAPITAL", ""),
        "Nombre Comercial:":          pares.get("NOMBRE COMERCIAL", ""),
        "Fecha inicio de operaciones:": pares.get("FECHA DE INICIO DE OPERACIONES", ""),

        # 3. Domicilio — columna izquierda
        "Código Postal:":         pares.get("CP", "") or pares.get("CODIGO POSTAL", ""),
        "Nombre de Vialidad:":    pares.get("NOMBRE DE LA VIALIDAD", ""),
        "Número Interior:":       pares.get("NUMERO INTERIOR", ""),
        "Nombre de la Localidad:": localidad,
        "Nombre de la Entidad Federativa:": pares.get("ENTIDAD FEDERATIVA", ""),

        # 4. Domicilio — columna derecha
        "Tipo de Vialidad:":    pares.get("TIPO DE VIALIDAD", ""),
        "Número Exterior:":     pares.get("NUMERO EXTERIOR", ""),
        "Nombre de la Colonia:": pares.get("COLONIA", ""),
        "Nombre del Municipio o Demarcación Territorial:": municipio,
        "Entre Calle:":         pares.get("ENTRE CALLE", ""),
    }


def procesar_texto_a_diccionario(file_stream, is_pdf=True):
    palabras = []
    texto_lineas_list = []
    MITAD_PAGINA = 306.0  # Valor por defecto carta (612 / 2)

    if is_pdf:
        try:
            doc = fitz.open(stream=file_stream, filetype="pdf")
            for p_idx, pagina in enumerate(doc):
                if p_idx == 0:
                    MITAD_PAGINA = pagina.rect.width / 2
                offset_y = p_idx * 10000.0
                for w in pagina.get_text("words"):
                    # Desplazar Y por página para que cada página mantenga sus filas aisladas
                    palabras.append((w[0], w[1] + offset_y, w[2], w[3] + offset_y, w[4]))
                texto_pag = pagina.get_text("text")
                if texto_pag:
                    texto_lineas_list.append(texto_pag)
            doc.close()
        except Exception:
            pass

    texto_lineas = "\n".join(texto_lineas_list)

    # ── BÚSQUEDA POR PALABRAS (método principal) ────────────────────────────
    ETIQUETAS_SAT = [
        "RFC", "CURP", "NOMBRE (S)", "PRIMER APELLIDO", "SEGUNDO APELLIDO",
        "CODIGO POSTAL", "TIPO DE VIALIDAD", "NOMBRE DE VIALIDAD",
        "NUMERO EXTERIOR", "NUMERO INTERIOR", "NOMBRE DE LA COLONIA",
        "NOMBRE DE LA LOCALIDAD", "MUNICIPIO O DEMARCACION", "ENTIDAD FEDERATIVA",
        "ENTRE CALLE", "CEDULA DE IDENTIFICACION", "DENOMINACION/RAZON SOCIAL",
        "FECHA INICIO DE OPERACIONES", "ESTATUS EN EL PADRON", "NOMBRE COMERCIAL",
        "REGIMEN CAPITAL", "DATOS DEL DOMICILIO", "IDENTIFICACION FISCAL",
        "DATOS DE IDENTIFICACION", "PAGINA ["
    ]

    def es_etiqueta_sat(texto: str) -> bool:
        t = _normalizar(texto).strip()
        if not t:
            return False
        return any(etiq in t for etiq in ETIQUETAS_SAT)

    def encontrar_etiquetas(etiqueta):
        """
        Busca todas las apariciones de la etiqueta normalizando acentos en todas las páginas.
        Devuelve lista de (x1, y0, y1) de la última palabra de cada coincidencia.
        """
        partes = _normalizar(etiqueta).replace(":", "").split()
        n = len(partes)
        coincidencias = []
        if not partes or not palabras:
            return coincidencias

        for i in range(len(palabras)):
            segmento = [
                _normalizar(palabras[i + j][4]).replace(":", "").strip()
                for j in range(n)
                if i + j < len(palabras)
            ]
            if segmento == partes:
                ultima = palabras[i + n - 1]
                coincidencias.append((ultima[2], ultima[1], ultima[3]))
        return coincidencias

    def extraer_valor_palabras(etiqueta, margen_y=8, max_x=None):
        coincidencias = encontrar_etiquetas(etiqueta)
        if not coincidencias:
            return None

        for t_x1, t_y0, t_y1 in coincidencias:
            resultado = []
            for p in palabras:
                x0, y0, x1, y1, texto = p[0], p[1], p[2], p[3], p[4]
                en_misma_fila = (abs(y0 - t_y0) < margen_y or abs(y1 - t_y1) < margen_y)
                a_la_derecha  = x0 > t_x1
                dentro_col    = (max_x is None or x0 < max_x)
                if a_la_derecha and en_misma_fila and dentro_col:
                    resultado.append(texto.strip())

            cand = " ".join(resultado).strip()
            if cand and not es_etiqueta_sat(cand):
                return cand
        return None

    # ── BÚSQUEDA POR LÍNEAS DE TEXTO (fallback) ─────────────────────────────
    def extraer_valor_lineas(etiqueta, permitir_vacio=False):
        """
        Busca la etiqueta en el texto plano línea por línea.
        Captura el valor aunque esté pegado (Código Postal:56900)
        o en la siguiente línea.
        """
        etiq_norm = _normalizar(etiqueta).replace(":", "").strip()
        lineas = texto_lineas.splitlines()

        for i, linea in enumerate(lineas):
            linea_norm = _normalizar(linea)
            if etiq_norm in linea_norm:
                partes = re.split(r":\s*", linea, maxsplit=1)
                if len(partes) == 2:
                    valor = partes[1].strip()
                    if valor and not es_etiqueta_sat(valor):
                        return valor
                    if i + 1 < len(lineas):
                        siguiente = lineas[i + 1].strip()
                        if siguiente and not es_etiqueta_sat(siguiente):
                            return siguiente
        return ""

    def extraer(etiqueta, max_x=None, permitir_vacio=False):
        valor = extraer_valor_palabras(etiqueta, max_x=max_x)
        if valor:
            return valor
        return extraer_valor_lineas(etiqueta, permitir_vacio=permitir_vacio)

    # ── RETORNO POR TEXTO NATIVO ─────────────────────────────────────────────
    rfc_ext = extraer("RFC:")
    curp_ext = extraer("CURP:")
    fecha_nac_auto = extraer_fecha_nac_de_rfc_o_curp(rfc_ext, curp_ext)

    resultado_texto = {
        # 1. Identidad Persona Física
        "RFC:":            rfc_ext,
        "CURP:":           curp_ext,
        "Nombre (s):":     extraer("Nombre (s):"),
        "Primer Apellido:":  extraer("Primer Apellido:"),
        "Segundo Apellido:": extraer("Segundo Apellido:"),
        "Fecha_nac":       fecha_nac_auto,

        # 2. Identidad Persona Moral
        "Denominación/Razón Social:": extraer("Denominación/Razón Social:"),
        "Régimen Capital:":           extraer("Capital:"),
        "Nombre Comercial:":          extraer("Comercial:", max_x=MITAD_PAGINA),
        "Fecha inicio de operaciones:": extraer("operaciones:"),

        # 3. Domicilio — columna izquierda (limitado a mitad de página)
        "Código Postal:":         extraer("Código Postal:", max_x=MITAD_PAGINA),
        "Nombre de Vialidad:":    extraer("Nombre de Vialidad:", max_x=MITAD_PAGINA),
        "Número Interior:":       extraer("Número Interior:", max_x=MITAD_PAGINA),
        "Nombre de la Localidad:": extraer("Nombre de la Localidad:", max_x=MITAD_PAGINA),
        "Nombre de la Entidad Federativa:": extraer("Entidad Federativa:", max_x=MITAD_PAGINA),

        # 4. Domicilio — columna derecha
        "Tipo de Vialidad:":    extraer("Tipo de Vialidad:"),
        "Número Exterior:":     extraer("Número Exterior:"),
        "Nombre de la Colonia:": extraer("Nombre de la Colonia:"),
        "Nombre del Municipio o Demarcación Territorial:": extraer("Demarcación Territorial:"),
        "Entre Calle:":         extraer("Entre Calle:"),
    }

    # ── FALLBACK AUTOMÁTICO QR SAT (para PDFs escaneados o imágenes JPG/PNG) ──
    campos_clave = (
        resultado_texto.get("RFC:"),
        resultado_texto.get("Nombre (s):"),
        resultado_texto.get("Denominación/Razón Social:"),
        resultado_texto.get("Código Postal:"),
    )
    if not any(c and str(c).strip() for c in campos_clave):
        urls_qr = _detectar_urls_qr_sat(file_stream, is_pdf=is_pdf)
        datos_qr = _consultar_validador_qr_sat(urls_qr)
        if datos_qr:
            return datos_qr

    return resultado_texto


def extraer_datos_memoria(file_bytes, is_pdf=True):
    """Función principal que llama app.py."""
    return procesar_texto_a_diccionario(file_bytes, is_pdf=is_pdf)
