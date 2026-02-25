import re
import fitz  # PyMuPDF
import easyocr
import numpy as np
import cv2


def procesar_texto_a_diccionario(texto):
    # Unificamos el texto en una sola línea para evitar que los saltos de página rompan la búsqueda
    texto = " ".join(texto.split())

    # Patrones ajustados a tu lista directa de la constancia
    patterns = {
        "RFC:": r"RFC:\s*([A-Z0-9]{12,13})",
        "CURP:": r"CURP:\s*([A-Z0-9]{18})",
        "Nombre (s):": r"NOMBRE\s*\(S\):\s*([A-Z\sÁÉÍÓÚÑ]+?)(?=\s*PRIMER|Primer|$)",
        "Primer Apellido:": r"PRIMER APELLIDO:\s*([A-Z\sÁÉÍÓÚÑ]+?)(?=\s*SEGUNDO|Segundo|$)",
        "Segundo Apellido:": r"SEGUNDO APELLIDO:\s*([A-Z\sÁÉÍÓÚÑ]+?)(?=\s*FECHA|Fecha|$)",
        "Código Postal:": r"CÓDIGO POSTAL:\s*(\d{5})",
        "Tipo de Vialidad:": r"TIPO DE VIALIDAD:\s*([A-Z\sÁÉÍÓÚÑ]+?)(?=\s*NOMBRE|Nombre|$)",
        "Nombre de Vialidad:": r"NOMBRE DE VIALIDAD:\s*([A-Z\s0-9ÁÉÍÓÚÑ]+?)(?=\s*NÚMERO|Número|$)",
        "Número Exterior:": r"NÚMERO EXTERIOR:\s*([A-Z0-9\s.-]+?)(?=\s*NÚMERO|Número|$)",
        "Número Interior:": r"NÚMERO INTERIOR:\s*([A-Z0-9\s.-]+?)(?=\s*NOMBRE|Nombre|$)",
        "Nombre de Colonia:": r"NOMBRE DE\s*(?:LA)?\s*COLONIA:\s*([A-Z\sÁÉÍÓÚÑ]+?)(?=\s*NOMBRE|Nombre|$)",
        "Nombre de la Localidad:": r"NOMBRE DE LA LOCALIDAD:\s*([A-Z\sÁÉÍÓÚÑ]+?)(?=\s*NOMBRE|Nombre|$)",
        "Nombre de Municipio o Demarcación Territorial:": r"NOMBRE DEL? MUNICIPIO O DEMARCACIÓN TERRITORIAL:\s*([A-Z\sÁÉÍÓÚÑ]+?)(?=\s*NOMBRE|Nombre|$)",
        "Nombre de la Entidad Federativa:": r"NOMBRE DE LA ENTIDAD FEDERATIVA:\s*([A-Z\sÁÉÍÓÚÑ]+?)(?=\s*ENTRE|Entre|$)"
    }

    resultados = {}
    for campo, ptr in patterns.items():
        # Buscamos ignorando mayúsculas/minúsculas para mayor seguridad
        match = re.search(ptr, texto, re.IGNORECASE)
        resultados[campo] = match.group(1).strip() if match else ""
    return resultados


def extraer_datos_memoria(file_bytes, is_pdf=True):
    texto_extraido = ""
    if is_pdf:
        try:
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            for pagina in doc:
                # El modo "blocks" ayuda a mantener juntas las palabras de una misma etiqueta
                texto_extraido += pagina.get_text("text") + " "
            doc.close()
        except Exception as e:
            print(f"Error digital: {e}")

    # Si es imagen o el PDF digital no soltó texto, usamos OCR
    if len(texto_extraido.strip()) < 50:
        try:
            nparr = np.frombuffer(file_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if is_pdf and img is None:
                doc = fitz.open(stream=file_bytes, filetype="pdf")
                pix = doc[0].get_pixmap(
                    matrix=fitz.Matrix(3, 3))  # Alta resolución
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

    return procesar_texto_a_diccionario(texto_extraido.upper())
