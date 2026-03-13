import re
import fitz


def procesar_texto_a_diccionario(file_stream):
    doc = fitz.open(stream=file_stream, filetype="pdf")
    pagina = doc[0]
    # Extraemos palabras con coordenadas exactas
    palabras = pagina.get_text("words")
    doc.close()

    def extraer_dato_segunda_columna(etiqueta_buscada):
        t_x1, t_y0, t_y1 = None, None, None

        # 1. Localizar la etiqueta en la columna izquierda
        for p in palabras:
            x0, y0, x1, y1, texto, b_no, l_no, w_no = p
            # Buscamos coincidencia parcial (por si falta o sobra el ":")
            if etiqueta_buscada.upper().strip(":") in texto.upper():
                t_x1, t_y0, t_y1 = x1, y0, y1
                break

        if t_x1 is None:
            return ""

        # 2. Extraer el dato en la columna de la derecha (misma fila)
        dato_final = []
        for p in palabras:
            x0, y0, x1, y1, texto, b_no, l_no, w_no = p

            # Condición: Estar a la derecha de la etiqueta y en la misma franja horizontal (margen 4px)
            if x0 >= t_x1 and (abs(y0 - t_y0) < 4 or abs(y1 - t_y1) < 4):
                # Freno: Si encontramos otra etiqueta con ":" nos detenemos
                if ":" in texto and texto.upper().strip(":") != etiqueta_buscada.upper().strip(":"):
                    break

                # Limpiar el texto para que no se repita la etiqueta en el resultado
                limpio = texto.replace(etiqueta_buscada, "").strip(" :")
                if limpio:
                    dato_final.append(limpio)

        return " ".join(dato_final).strip()

    # --- SOLO BLOQUE 1: IDENTIDAD ---
    return {
        "RFC:": extraer_dato_segunda_columna("RFC:"),
        "CURP:": extraer_dato_segunda_columna("CURP:"),
        "Nombre (s):": extraer_dato_segunda_columna("Nombre (s):"),
        "Primer Apellido:": extraer_dato_segunda_columna("Primer Apellido:"),
        "Segundo Apellido:": extraer_dato_segunda_columna("Segundo Apellido:")
    }


def extraer_datos_memoria(file_bytes, is_pdf=True):
    return procesar_texto_a_diccionario(file_bytes)
