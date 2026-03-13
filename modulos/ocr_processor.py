import re
import fitz
import numpy as np
import cv2
import easyocr


def procesar_texto_a_diccionario(pdf_path_or_stream):
    # Abrimos el documento con PyMuPDF para obtener coordenadas exactas
    doc = fitz.open(stream=pdf_path_or_stream, filetype="pdf")
    pagina = doc[0]  # Generalmente los datos están en la primera página

    # Obtenemos todas las palabras con sus posiciones (x, y, ancho, alto)
    palabras = pagina.get_text("words")

    res = {k: "" for k in [
        "RFC:", "CURP:", "Nombre (s):", "Primer Apellido:", "Segundo Apellido:",
        "Código Postal:", "Tipo de Vialidad:", "Nombre de Vialidad:",
        "Número Exterior:", "Número Interior:", "Nombre de la Colonia:",
        "Nombre de la Localidad:", "Nombre del Municipio o Demarcación Territorial:",
        "Nombre de la Entidad Federativa:"
    ]}

    # Función para buscar qué hay a la derecha de una etiqueta
    def buscar_a_la_derecha(etiqueta_texto, umbral_y=5):
        # 1. Encontrar la etiqueta en la página
        etiqueta_texto = etiqueta_texto.upper().replace(":", "")
        hits = pagina.search_for(etiqueta_texto)
        if not hits:
            return ""

        # Tomamos el primer hallazgo
        rect_etiqueta = hits[0]

        # 2. Buscar palabras que estén en la misma línea (Y similar) y a la derecha (X mayor)
        candidatos = []
        for p in palabras:
            x0, y0, x1, y1, texto, block_no, line_no, word_no = p
            # ¿Está en la misma franja horizontal?
            if abs(y0 - rect_etiqueta.y0) < umbral_y:
                # ¿Está a la derecha?
                if x0 > rect_etiqueta.x0:
                    candidatos.append((x0, texto))

        # Ordenamos de izquierda a derecha y unimos
        candidatos.sort()
        # Filtramos para no repetir la propia etiqueta si se coló
        resultado = " ".join(
            [c[1] for c in candidatos if c[1].upper() not in etiqueta_texto])
        return resultado.strip(" :")

    # Mapeo directo usando las etiquetas de tus imágenes
    res["RFC:"] = buscar_a_la_derecha("RFC")
    res["CURP:"] = buscar_a_la_derecha("CURP")
    res["Nombre (s):"] = buscar_a_la_derecha("Nombre (s)")
    res["Primer Apellido:"] = buscar_a_la_derecha("Primer Apellido")
    res["Segundo Apellido:"] = buscar_a_la_derecha("Segundo Apellido")
    res["Código Postal:"] = buscar_a_la_derecha("Código Postal")
    res["Tipo de Vialidad:"] = buscar_a_la_derecha("Tipo de Vialidad")
    res["Nombre de Vialidad:"] = buscar_a_la_derecha("Nombre de Vialidad")
    res["Número Exterior:"] = buscar_a_la_derecha("Número Exterior")
    res["Número Interior:"] = buscar_a_la_derecha("Número Interior")
    res["Nombre de la Colonia:"] = buscar_a_la_derecha("Nombre de la Colonia")
    res["Nombre de la Localidad:"] = buscar_a_la_derecha(
        "Nombre de la Localidad")
    res["Nombre del Municipio o Demarcación Territorial:"] = buscar_a_la_derecha(
        "Territorial")
    res["Nombre de la Entidad Federativa:"] = buscar_a_la_derecha(
        "Entidad Federativa")

    doc.close()
    return res


def extraer_datos_memoria(file_bytes, is_pdf=True):
    # Esta versión es mucho más precisa para tablas
    try:
        return procesar_texto_a_diccionario(file_bytes)
    except Exception as e:
        print(f"Error en extracción: {e}")
        return {k: "ERROR" for k in ["RFC:", "Nombre (s):"]}  # Fallback
