import re
import fitz  # PyMuPDF
import easyocr
import numpy as np
import cv2


def procesar_texto_a_diccionario(texto):
    # Paso 1: Limpieza agresiva del texto (quitar saltos de línea y espacios dobles)
    texto = " ".join(texto.split())

    patterns = {
        "Nombre (s):": r"(?:NOMBRE\s*\(S\):|Nombre\(s\))\s*([A-Z\sÁÉÍÓÚÑ]+?)(?=\s*PRIMER|Primer|$)",
        "Primer Apellido:": r"(?:PRIMER APELLIDO:|Primer Apellido)\s*([A-Z\sÁÉÍÓÚÑ]+?)(?=\s*SEGUNDO|Segundo|$)",
        "Segundo Apellido:": r"(?:SEGUNDO APELLIDO:|Segundo Apellido)\s*([A-Z\sÁÉÍÓÚÑ]+?)(?=\s*FECHA|Fecha|$)",
        "RFC:": r"RFC:\s*([A-Z0-9]{12,13})",
        "CURP:": r"CURP:\s*([A-Z0-9]{18})",
        "Nombre de Vialidad:": r"(?:NOMBRE DE VIALIDAD:|Nombre de Vialidad)\s*([A-Z\s0-9ÁÉÍÓÚÑ]+?)(?=\s*NÚMERO|Número|$)",
        "Tipo de Vialidad:": r"(?:TIPO DE VIALIDAD:|Tipo de Vialidad)\s*([A-Z\sÁÉÍÓÚÑ]+?)(?=\s*NOMBRE|Nombre|$)",
        "Número Exterior:": r"(?:NÚMERO EXTERIOR:|Número Exterior)\s*([A-Z0-9\s.-]+?)(?=\s*NÚMERO|Número|$)",
        "Número Interior:": r"(?:NÚMERO INTERIOR:|Número Interior)\s*([A-Z0-9\s.-]+?)(?=\s*NOMBRE|Nombre|$)",
        "Nombre de la Colonia:": r"(?:NOMBRE DE LA COLONIA:|Nombre de la Colonia)\s*([A-Z\sÁÉÍÓÚÑ]+?)(?=\s*NOMBRE|Nombre|$)",
        "Nombre de la Localidad:": r"(?:NOMBRE DE LA LOCALIDAD:|Nombre de la Localidad)\s*([A-Z\sÁÉÍÓÚÑ]+?)(?=\s*NOMBRE|Nombre|$)",
        "Nombre del Municipio o Demarcación Territorial:": r"(?:NOMBRE DEL MUNICIPIO O DEMARCACIÓN TERRITORIAL:|Municipio)\s*([A-Z\sÁÉÍÓÚÑ]+?)(?=\s*NOMBRE|Nombre|$)",
        "Nombre de la Entidad Federativa:": r"(?:NOMBRE DE LA ENTIDAD FEDERATIVA:|Entidad Federativa)\s*([A-Z\sÁÉÍÓÚÑ]+?)(?=\s*ENTRE|Entre|$)",
        "Código Postal:": r"(?:CÓDIGO\s*POSTAL\s*:|Código Postal)\s*(\d{5})"
    }

    resultados = {}
    for campo, ptr in patterns.items():
        match = re.search(ptr, texto, re.IGNORECASE)
        if match:
            resultados[campo] = match.group(1).strip()
        else:
            resultados[campo] = ""
    return resultados


def extraer_datos_memoria(file_bytes, is_pdf=True):
    texto_extraido = ""
    img = None

    if is_pdf:
        try:
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            for pagina in doc:
                # Usamos el método "text" que es más fiable para PDFs digitales
                texto_extraido += pagina.get_text("text") + " "
            doc.close()
        except Exception as e:
            print(f"Error digital: {e}")

    # Si no extrajo nada digitalmente, forzamos OCR
    if len(texto_extraido.strip()) < 50:
        try:
            nparr = np.frombuffer(file_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if is_pdf and img is None:
                doc = fitz.open(stream=file_bytes, filetype="pdf")
                # Aumentamos la resolución para que el OCR no falle (Matrix 3x3)
                pix = doc[0].get_pixmap(matrix=fitz.Matrix(3, 3))
                img_data = np.frombuffer(
                    pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
                img = cv2.cvtColor(img_data, cv2.COLOR_RGB2BGR)
                doc.close()

            if img is not None:
                reader = easyocr.Reader(['es'])
                resultados = reader.readtext(img, detail=0)
                texto_extraido = " ".join(resultados)
        except Exception as e:
            print(f"Error OCR: {e}")

    # DEPURACIÓN: Esto imprimirá en la consola lo que el código está "viendo"
    print("--- TEXTO DETECTADO ---")
    print(texto_extraido[:500])

    return procesar_texto_a_diccionario(texto_extraido.upper())
