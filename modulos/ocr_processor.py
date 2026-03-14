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

        for i, p in enumerate(palabras):
            # Intentamos hacer match de n palabras consecutivas
            segmento = [palabras[i + j][4].upper().replace(":", "").strip()
                        for j in range(n)
                        if i + j < len(palabras)]

            if segmento == partes:
                # Retornamos x1, y0, y1 de la ÚLTIMA palabra de la etiqueta
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

    return {
        "RFC":            extraer_valor("RFC:"),
        "CURP":           extraer_valor("CURP:"),
        "Nombre":         extraer_valor("Nombre (s):"),
        "Primer Apellido":  extraer_valor("Primer Apellido:"),
        "Segundo Apellido": extraer_valor("Segundo Apellido:")
    }


def extraer_datos_memoria(file_bytes, is_pdf=True):
    return procesar_texto_a_diccionario(file_bytes)
