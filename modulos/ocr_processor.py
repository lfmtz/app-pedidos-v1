import re
import fitz
import easyocr
import numpy as np
import cv2


def procesar_texto_a_diccionario(texto):
    # Usamos tus patrones originales que ya sabes que funcionan para todas las columnas
    patterns = {
        "Nombre (s):": r"NOMBRE\s*\(S\):\s*([A-Z\s]+?)(?=\s*PRIMER|$)",
        "Primer Apellido:": r"PRIMER APELLIDO:\s*([A-Z\s]+?)(?=\s*SEGUNDO|$)",
        "Segundo Apellido:": r"SEGUNDO APELLIDO:\s*([A-Z\s]+?)(?=\s*FECHA|$)",
        "RFC:": r"RFC:\s*([A-Z0-9]{12,13})",
        "CURP:": r"CURP:\s*([A-Z0-9]{18})",
        "Nombre de Vialidad:": r"NOMBRE DE VIALIDAD:\s*([A-Z\s0-9]+?)(?=\s*NÚMERO|$)",
        "Tipo de Vialidad:": r"TIPO DE VIALIDAD:\s*([A-Z\s]+?)(?=\s*NOMBRE|$)",
        "Número Exterior:": r"NÚMERO EXTERIOR:\s*([A-Z0-9\s.-]+?)(?=\s*NÚMERO|$)",
        "Número Interior:": r"NÚMERO INTERIOR:\s*([A-Z0-9\s.-]+?)(?=\s*NOMBRE|$)",
        "Nombre de la Colonia:": r"NOMBRE DE LA COLONIA:\s*([A-Z\s]+?)(?=\s*NOMBRE|$)",
        "Nombre de la Localidad:": r"NOMBRE DE LA LOCALIDAD:\s*([A-Z\s]+?)(?=\s*NOMBRE|$)",
        "Nombre del Municipio o Demarcación Territorial:": r"NOMBRE DEL MUNICIPIO O DEMARCACIÓN TERRITORIAL:\s*([A-Z\s]+?)(?=\s*NOMBRE|$)",
        "Nombre de la Entidad Federativa:": r"NOMBRE DE LA ENTIDAD FEDERATIVA:\s*([A-Z\s]+?)(?=\s*ENTRE|$)",
        "Código Postal:": r"CÓDIGO\s*POSTAL\s*:\s*(\d{5})"
    }

    resultados = {}
    for campo, ptr in patterns.items():
        match = re.search(ptr, texto, re.IGNORECASE)
        resultados[campo] = match.group(1).strip() if match else ""

    return resultados


def extraer_datos_memoria(file_bytes, is_pdf=True):
    """
    Versión para Streamlit que recibe bytes y asegura compatibilidad 
    de imagen para EasyOCR en la nube.
    """
    texto_extraido = ""

    # 1. Extracción de texto digital (si es PDF)
    if is_pdf:
        try:
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            for pagina in doc:
                texto_extraido += pagina.get_text()
            doc.close()
        except Exception as e:
            print(f"Error en extracción digital: {e}")

    # 2. Si el PDF es una imagen o el texto es muy corto, usamos OCR
    if len(texto_extraido.strip()) < 50:
        # Inicializamos el lector en español
        reader = easyocr.Reader(['es'])

        try:
            # --- SOLUCIÓN AL ERROR CV2 ---
            # Convertimos los bytes a un array de numpy
            nparr = np.frombuffer(file_bytes, np.uint8)
            # Decodificamos el array a una imagen que OpenCV entienda
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if img is not None:
                # Si la decodificación funcionó, pasamos la imagen procesada
                resultados = reader.readtext(img, detail=0)
            else:
                # Si falla (por ser un PDF complejo), intentamos pasar los bytes
                # pero es más probable que el error cv2 persista sin packages.txt
                resultados = reader.readtext(file_bytes, detail=0)

            texto_extraido = " ".join(resultados)
        except Exception as e:
            print(f"Error en OCR: {e}")
            texto_extraido = ""

    # Procesamos el texto final (forzado a mayúsculas)
    return procesar_texto_a_diccionario(texto_extraido.upper())
