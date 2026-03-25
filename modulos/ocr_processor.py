import fitz


def procesar_texto_a_diccionario(file_stream):
    doc = fitz.open(stream=file_stream, filetype="pdf")
    pagina = doc[0]
    palabras = pagina.get_text("words")
    MITAD_PAGINA = pagina.rect.width / 2  # ✅ límite de columna automático
    doc.close()

    def encontrar_etiqueta(etiqueta):
        """
        Busca una etiqueta que puede estar dividida en varias palabras.
        Retorna las coordenadas de la última palabra de la etiqueta encontrada.
        """
        partes = etiqueta.upper().replace(":", "").split()
        n = len(partes)

        for i in range(len(palabras)):
            segmento = [
                palabras[i + j][4].upper().replace(":", "").strip()
                for j in range(n)
                if i + j < len(palabras)
            ]
            if segmento == partes:
                ultima = palabras[i + n - 1]
                return ultima[2], ultima[1], ultima[3]  # x1, y0, y1

        return None, None, None

    def extraer_valor(etiqueta, margen_y=8, max_x=None):
        t_x1, t_y0, t_y1 = encontrar_etiqueta(etiqueta)
        if t_x1 is None:
            return ""

        dato_final = []
        for p in palabras:
            x0, y0, x1, y1, texto = p[0], p[1], p[2], p[3], p[4]
            en_misma_fila = (
                abs(y0 - t_y0) < margen_y or abs(y1 - t_y1) < margen_y)
            a_la_derecha = x0 > t_x1
            dentro_columna = (max_x is None or x0 < max_x)  # ✅ nuevo límite

            if a_la_derecha and en_misma_fila and dentro_columna:
                dato_final.append(texto.strip())

        return " ".join(dato_final).strip()

    # ── AJUSTE DE LLAVES PARA COMPATIBILIDAD CON SHEETS ──────────────────
    # He renombrado las llaves para que coincidan con los encabezados estándar
    # y asegurar que la inyección no falle por nombres diferentes.

    return {
        # Identidad
        "RFC:": extraer_valor("RFC:"),
        "CURP:": extraer_valor("CURP:"),
        "Nombre (s):": extraer_valor("Nombre (s):"),
        "Primer Apellido:": extraer_valor("Primer Apellido:"),
        "Segundo Apellido:": extraer_valor("Segundo Apellido:"),

        # Domicilio (Columna Izquierda) - Usamos MITAD_PAGINA para no invadir la derecha
        "Código Postal:": extraer_valor("Código Postal:", max_x=MITAD_PAGINA),
        "Nombre de Vialidad:": extraer_valor("Nombre de Vialidad:", max_x=MITAD_PAGINA),
        "Número Interior:": extraer_valor("Número Interior:", max_x=MITAD_PAGINA),
        "Nombre de la Localidad:": extraer_valor("Nombre de la Localidad:", max_x=MITAD_PAGINA),
        "Nombre de la Entidad Federativa:": extraer_valor("Federativa:", max_x=MITAD_PAGINA),

        # Domicilio (Columna Derecha)
        "Tipo de Vialidad:": extraer_valor("Tipo de Vialidad:"),
        "Número Exterior:": extraer_valor("Número Exterior:"),
        "Nombre de la Colonia:": extraer_valor("Nombre de la Colonia:"),
        "Nombre del Municipio o Demarcación Territorial:": extraer_valor("Territorial:"),
    }


def extraer_datos_memoria(file_bytes, is_pdf=True):
    # Esta es la función que llama tu bot o tu script principal
    return procesar_texto_a_diccionario(file_bytes)
