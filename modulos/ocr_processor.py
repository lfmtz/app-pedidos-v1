import re
import fitz  # PyMuPDF para manejar PDFs
import easyocr  # Para OCR tradicional si el QR falla
import numpy as np  # Para manejo de matrices de imagen
import cv2  # OpenCV para procesamiento de imagen
from pyzbar.pyzbar import decode  # La nueva librería para leer QRs
import requests  # Para "viajar" a la liga del QR
from bs4 import BeautifulSoup  # Para extraer datos de esa liga


def procesar_texto_a_diccionario(texto):
    # Usamos tus patrones originales que ya sabes que funcionan para todas las columnas
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
    texto_extraido = ""
    url_encontrada = None

    # 1. Extracción digital rápida
    if is_pdf:
        try:
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            for pagina in doc:
                texto_extraido += pagina.get_text()

            # --- MEJORA AQUÍ: Si no hay texto, convertimos la página a imagen para el QR ---
            if len(texto_extraido.strip()) < 50:
                pagina = doc[0]
                # Zoom para mejor lectura
                pix = pagina.get_pixmap(matrix=fitz.Matrix(2, 2))
                img_data = np.frombuffer(
                    pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
                img = cv2.cvtColor(img_data, cv2.COLOR_RGB2BGR)
            else:
                img = None
            doc.close()
        except Exception as e:
            print(f"Error en extracción digital/conversión: {e}")
            img = None
    else:
        # Si es una imagen directa (jpg/png)
        nparr = np.frombuffer(file_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    # 2. Lógica de QR y OCR
    if len(texto_extraido.strip()) < 50 and img is not None:
        try:
            # BUSCAMOS EL QR
            qr_codes = decode(img)
            if qr_codes:
                url_encontrada = qr_codes[0].data.decode('utf-8')
                if "sat.gob.mx" in url_encontrada:
                    texto_extraido = extraer_datos_de_url_sat(url_encontrada)

            # SI NO HUBO QR O FALLÓ LA URL, HACEMOS OCR
            if not texto_extraido.strip():
                reader = easyocr.Reader(['es'])
                resultados = reader.readtext(img, detail=0)
                texto_extraido = " ".join(resultados)
        except Exception as e:
            print(f"Error en proceso QR/OCR: {e}")

    return procesar_texto_a_diccionario(texto_extraido.upper())


def extraer_datos_de_url_sat(url):
    try:
        response = requests.get(url, timeout=10)
        # Usamos BeautifulSoup para obtener solo el texto visible de la página
        soup = BeautifulSoup(response.text, 'html.parser')

        # El SAT organiza los datos en tablas o etiquetas de texto
        texto_pagina = soup.get_text(separator=" ")

        # Limpiamos el texto para que sea compatible con tus Regex
        return texto_pagina.upper()
    except Exception as e:
        print(f"Error al conectar con el SAT: {e}")
        return ""
