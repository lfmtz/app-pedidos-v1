import re
import fitz


def procesar_texto_a_diccionario(file_stream):
    doc = fitz.open(stream=file_stream, filetype="pdf")
    pagina = doc[0]
    # Obtenemos las palabras con sus coordenadas (x0, y0, x1, y1, texto, ...)
    palabras = pagina.get_text("words")
    doc.close()

    def extraer_dato_columna_derecha(etiqueta_buscada):
        target_x1 = None
        target_y0 = None
        target_y1 = None

        # 1. Localizar la etiqueta (Columna 1)
        for p in palabras:
            x0, y0, x1, y1, texto, block_no, line_no, word_no = p
            # Buscamos la etiqueta exacta (ej. "RFC:")
            if etiqueta_buscada.upper() in texto.upper():
                target_x1 = x1  # Límite derecho de la etiqueta
                target_y0 = y0  # Altura superior
                target_y1 = y1  # Altura inferior
                break

        if target_x1 is None:
            return ""

        # 2. Capturar lo que esté a la derecha en la misma fila (Columna 2)
        dato_encontrado = []
        for p in palabras:
            x0, y0, x1, y1, texto, block_no, line_no, word_no = p
            # ¿Está a la derecha? y ¿Está en la misma franja de altura (margen de 3px)?
            if x0 >= target_x1 and (abs(y0 - target_y0) < 3 or abs(y1 - target_y1) < 3):
                # Evitamos capturar la propia etiqueta si se repite
                if texto.upper().strip(":") != etiqueta_buscada.upper().strip(":"):
                    dato_encontrado.append(texto)

        return " ".join(dato_encontrado).strip()

    # --- TEST DE IDENTIDAD POR COLUMNAS ---
    return {
        "RFC:": extraer_dato_columna_derecha("RFC:"),
        "CURP:": extraer_dato_columna_derecha("CURP:"),
        "Nombre (s):": extraer_dato_columna_derecha("Nombre (s):"),
        "Primer Apellido:": extraer_dato_columna_derecha("Primer Apellido:"),
        "Segundo Apellido:": extraer_dato_columna_derecha("Segundo Apellido:")
    }


def extraer_datos_memoria(file_bytes, is_pdf=True):
    return procesar_texto_a_diccionario(file_bytes)
