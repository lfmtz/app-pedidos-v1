import fitz


def procesar_texto_a_diccionario(file_stream):
    doc = fitz.open(stream=file_stream, filetype="pdf")
    pagina = doc[0]
    palabras = pagina.get_text("words")
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

    def extraer_valor(etiqueta, margen_y=8):
        t_x1, t_y0, t_y1 = encontrar_etiqueta(etiqueta)
        if t_x1 is None:
            return ""

        dato_final = []
        for p in palabras:
            x0, y0, x1, y1, texto = p[0], p[1], p[2], p[3], p[4]
            en_misma_fila = (
                abs(y0 - t_y0) < margen_y or abs(y1 - t_y1) < margen_y)
            a_la_derecha = x0 > t_x1

            if a_la_derecha and en_misma_fila:
                dato_final.append(texto.strip())

        return " ".join(dato_final).strip()

    # ── BLOQUE 1: IDENTIDAD ──────────────────────────────────────────────
    identidad = {
        "RFC":              extraer_valor("RFC:"),
        "CURP":             extraer_valor("CURP:"),
        "Nombre":           extraer_valor("Nombre (s):"),
        "Primer Apellido":  extraer_valor("Primer Apellido:"),
        "Segundo Apellido": extraer_valor("Segundo Apellido:"),
    }

    # ── BLOQUE 2: DOMICILIO ──────────────────────────────────────────────
    # ⚠️  Las etiquetas largas (Municipio, Entidad) se buscan por su
    #     fragmento FINAL porque get_text("words") las parte en tokens
    #     y la última palabra es única y suficiente para ubicar la fila.
    domicilio = {
        "Codigo Postal":       extraer_valor("Código Postal:"),
        "Tipo de Vialidad":    extraer_valor("Tipo de Vialidad:"),
        "Nombre de Vialidad":  extraer_valor("Nombre de Vialidad:"),
        "Numero Exterior":     extraer_valor("Número Exterior:"),
        "Numero Interior":     extraer_valor("Número Interior:"),
        "Nombre de la Colonia":    extraer_valor("Nombre de la Colonia:"),
        "Nombre de la Localidad":  extraer_valor("Nombre de la Localidad:"),
        # Se busca por el fragmento final exclusivo de cada etiqueta larga
        "Municipio o Demarcacion": extraer_valor("Territorial:"),
        "Entidad Federativa":      extraer_valor("Federativa:"),
    }

    return {**identidad, **domicilio}


def extraer_datos_memoria(file_bytes, is_pdf=True):
    return procesar_texto_a_diccionario(file_bytes)
