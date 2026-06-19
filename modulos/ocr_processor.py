"""
ocr_processor.py - Extracción de datos de Constancias de Situación Fiscal
Mejoras:
  - Normalización de acentos para búsqueda robusta (Código = Codigo)
  - Detección de valores pegados a la etiqueta (Código Postal:56900)
  - Búsqueda por líneas de texto como fallback cuando falla la búsqueda por palabras
"""
import fitz
import unicodedata
import re


def _normalizar(texto: str) -> str:
    """Elimina acentos y pasa a mayúsculas para comparación robusta."""
    texto = texto.upper()
    nfkd = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def procesar_texto_a_diccionario(file_stream):
    doc = fitz.open(stream=file_stream, filetype="pdf")
    pagina = doc[0]
    palabras = pagina.get_text("words")          # lista de (x0,y0,x1,y1,texto,...)
    texto_lineas = pagina.get_text("text")        # texto plano para fallback
    ancho = pagina.rect.width
    MITAD_PAGINA = ancho / 2
    doc.close()

    # ── BÚSQUEDA POR PALABRAS (método principal) ────────────────────────────
    def encontrar_etiqueta(etiqueta):
        """
        Busca la etiqueta normalizando acentos.
        Devuelve (x1, y0, y1) de la última palabra de la etiqueta.
        """
        partes = _normalizar(etiqueta).replace(":", "").split()
        n = len(partes)
        for i in range(len(palabras)):
            segmento = [
                _normalizar(palabras[i + j][4]).replace(":", "").strip()
                for j in range(n)
                if i + j < len(palabras)
            ]
            if segmento == partes:
                ultima = palabras[i + n - 1]
                return ultima[2], ultima[1], ultima[3]  # x1, y0, y1
        return None, None, None

    def extraer_valor_palabras(etiqueta, margen_y=8, max_x=None):
        t_x1, t_y0, t_y1 = encontrar_etiqueta(etiqueta)
        if t_x1 is None:
            return None   # None indica que no se encontró (usará fallback)

        resultado = []
        for p in palabras:
            x0, y0, x1, y1, texto = p[0], p[1], p[2], p[3], p[4]
            en_misma_fila = (abs(y0 - t_y0) < margen_y or abs(y1 - t_y1) < margen_y)
            a_la_derecha  = x0 > t_x1
            dentro_col    = (max_x is None or x0 < max_x)
            if a_la_derecha and en_misma_fila and dentro_col:
                resultado.append(texto.strip())

        return " ".join(resultado).strip() if resultado else None

    # ── BÚSQUEDA POR LÍNEAS DE TEXTO (fallback) ─────────────────────────────
    # Lista de etiquetas del SAT para validar que no capturamos la siguiente
    ETIQUETAS_SAT = [
        "RFC", "CURP", "NOMBRE", "PRIMER APELLIDO", "SEGUNDO APELLIDO",
        "CODIGO POSTAL", "TIPO DE VIALIDAD", "NOMBRE DE VIALIDAD",
        "NUMERO EXTERIOR", "NUMERO INTERIOR", "NOMBRE DE LA COLONIA",
        "NOMBRE DE LA LOCALIDAD", "MUNICIPIO", "ENTIDAD FEDERATIVA",
        "ENTRE CALLE", "CEDULA", "DENOMINACION", "FECHA INICIO",
        "ESTATUS", "NOMBRE COMERCIAL", "REGIMEN", "DATOS DEL DOMICILIO",
        "IDENTIFICACION FISCAL", "DATOS DE IDENTIFICACION", "PAGINA"
    ]

    def es_etiqueta_sat(texto: str) -> bool:
        t = _normalizar(texto)
        return any(etiq in t for etiq in ETIQUETAS_SAT)

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
                # Intentar extraer valor pegado después de ":"
                # Ej: "Código Postal:56900" → "56900"
                partes = re.split(r":\s*", linea, maxsplit=1)
                if len(partes) == 2:
                    valor = partes[1].strip()
                    # Verificar que el valor no sea en realidad otra etiqueta
                    if valor and not es_etiqueta_sat(valor):
                        return valor
                    # Buscar en la siguiente línea
                    if i + 1 < len(lineas):
                        siguiente = lineas[i + 1].strip()
                        if siguiente and not es_etiqueta_sat(siguiente):
                            return siguiente
        return ""

    def extraer(etiqueta, max_x=None, permitir_vacio=False):
        """
        Intenta primero con palabras; si falla usa líneas como fallback.
        """
        valor = extraer_valor_palabras(etiqueta, max_x=max_x)
        if valor:
            return valor
        # Fallback: búsqueda por líneas
        return extraer_valor_lineas(etiqueta, permitir_vacio=permitir_vacio)

    # ── RETORNO FINAL ────────────────────────────────────────────────────────
    return {
        # 1. Identidad Persona Física
        "RFC:":            extraer("RFC:"),
        "CURP:":           extraer("CURP:"),
        "Nombre (s):":     extraer("Nombre (s):"),
        "Primer Apellido:":  extraer("Primer Apellido:"),
        "Segundo Apellido:": extraer("Segundo Apellido:"),

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


def extraer_datos_memoria(file_bytes, is_pdf=True):
    """Función principal que llama app.py."""
    return procesar_texto_a_diccionario(file_bytes)
