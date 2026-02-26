import re
import fitz
import numpy as np
import cv2
import easyocr


def procesar_texto_a_diccionario(texto):
    # Tus patrones originales (Respetados al 100%)
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
        match = re.search(ptr, texto)
        resultados[campo] = match.group(1).strip() if match else ""
    return resultados


def extraer_datos_memoria(file_bytes, is_pdf=True):
    texto_extraido = ""

    # Manejo de PDF desde memoria
    if is_pdf:
        try:
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            for pagina in doc:
                texto_extraido += pagina.get_text()
            doc.close()
        except Exception as e:
            print(f"Error PDF: {e}")

    # Si el texto es muy corto, aplicamos OCR (Tu lógica original)
    if len(texto_extraido) < 50:
        try:
            # Convertimos bytes a imagen para EasyOCR
            nparr = np.frombuffer(file_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            reader = easyocr.Reader(['es'])
            resultados = reader.readtext(img, detail=0)
            texto_extraido = " ".join(resultados)
        except Exception as e:
            print(f"Error OCR: {e}")

    # Procesamos y añadimos el texto_bruto para el debug que pide app.py
    texto_final = texto_extraido.upper()
    datos = procesar_texto_a_diccionario(texto_final)
    datos["texto_bruto"] = texto_final

    return datos
