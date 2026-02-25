import re
import fitz  # PyMuPDF
import easyocr
import numpy as np
import cv2


def procesar_texto_a_diccionario(texto):
    """Analiza el texto y extrae los campos usando Regex."""
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
        resultados[campo] = match.group(1).strip() if match else ""
    return resultados


def extraer_datos_memoria(file_bytes, is_pdf=True):
    """Lee PDF digital o aplica OCR si es imagen/escaneado."""
    texto_extraido = ""
    img = None

    # 1. Intentar extracción de texto digital (PDF nativo)
    if is_pdf:
        try:
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            for pagina in doc:
                texto_extraido += pagina.get_text()

            # Si el PDF no tiene texto (es una imagen), lo preparamos para OCR
            if len(texto_extraido.strip()) < 50:
                pagina = doc[0]
                pix = pagina.get_pixmap(matrix=fitz.Matrix(2, 2))
                img_data = np.frombuffer(
                    pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
                img = cv2.cvtColor(img_data, cv2.COLOR_RGB2BGR)
            doc.close()
        except Exception as e:
            print(f"Error en lectura digital: {e}")
    else:
        # Si es una imagen (JPG/PNG)
        nparr = np.frombuffer(file_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    # 2. Si no hay texto digital, aplicar OCR
    if len(texto_extraido.strip()) < 50 and img is not None:
        try:
            reader = easyocr.Reader(['es'])
            resultados = reader.readtext(img, detail=0)
            texto_extraido = " ".join(resultados)
        except Exception as e:
            print(f"Error en OCR: {e}")

    return procesar_texto_a_diccionario(texto_extraido.upper())
