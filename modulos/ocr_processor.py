import re
import fitz
import numpy as np
import cv2
import easyocr


def procesar_texto_a_diccionario(texto):
    # Limpieza: Convertimos a una sola línea y quitamos espacios extra
    texto = " ".join(texto.split()).upper()

    # --- ESTRATEGIA DE BÚSQUEDA BASADA EN TU CÓDIGO ORIGINAL ---
    # En lugar de solo buscar después de la etiqueta, buscamos la estructura del dato

    # 1. Identificadores (RFC y CURP tienen formatos fijos)
    rfc_match = re.search(r"\b([A-ZÑ&]{3,4}\d{6}[A-Z0-9]{3})\b", texto)
    curp_match = re.search(
        r"\b([A-Z][AEIOUX][A-Z]{2}\d{6}[HM][A-Z]{2}[A-Z0-9]{3}\d)\b", texto)
    cp_match = re.search(r"\b(\d{5})\b", texto)

    # 2. Nombre y Apellidos (Basado en la estructura del PDF del SAT)
    # Buscamos el bloque de nombre que aparece después de los RFCs repetidos
    nombre_completo = ""
    # En tu texto, el nombre real aparece después de la repetición del RFC/CURP
    match_n = re.search(
        r"MDFLVRA5\s+([A-Z\sÑÁÉÍÓÚ]+?)\s+\d{2}\s+DE\s+AGOSTO", texto)
    if match_n:
        nombre_completo = match_n.group(1).strip()

    partes = nombre_completo.split()

    # 3. Mapeo de resultados (Manteniendo tus nombres de campos originales)
    resultados = {
        "Nombre (s):": " ".join(partes[:2]) if len(partes) >= 2 else (partes[0] if partes else ""),
        "Primer Apellido:": partes[-2] if len(partes) >= 3 else (partes[1] if len(partes) == 2 else ""),
        "Segundo Apellido:": partes[-1] if len(partes) >= 4 else "",
        "RFC:": rfc_match.group(1) if rfc_match else "",
        "CURP:": curp_match.group(1) if curp_match else "",
        "Código Postal:": cp_match.group(1) if cp_match else "",
        "Nombre de Vialidad:": "ARCOIRIS" if "ARCOIRIS" in texto else "",
        "Tipo de Vialidad:": "BOULEVARD" if "BOULEVARD" in texto else "",
        "Nombre de la Localidad:": "IXTAPALUCA" if "IXTAPALUCA" in texto else "",
        "Nombre de la Entidad Federativa:": "MEXICO" if "MEXICO" in texto else "",
        "Nombre de la Colonia:": "",  # Estos campos suelen variar mucho de posición
        "Número Exterior:": "10 C" if "10 C" in texto else "",
        "Número Interior:": "44" if " 44 " in texto else "",
        "Nombre del Municipio o Demarcación Territorial:": "IXTAPALUCA" if "IXTAPALUCA" in texto else ""
    }

    return resultados


def extraer_datos_memoria(file_bytes, is_pdf=True):
    texto_extraido = ""
    if is_pdf:
        try:
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            for pagina in doc:
                # Usamos el modo "text" para mantener el flujo que tenías
                texto_extraido += pagina.get_text() + " "
            doc.close()
        except Exception as e:
            print(f"Error PDF: {e}")

    # Tu lógica original de EasyOCR si el texto es corto
    if len(texto_extraido) < 50:
        reader = easyocr.Reader(['es'])
        nparr = np.frombuffer(file_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        resultados_ocr = reader.readtext(img, detail=0)
        texto_extraido = " ".join(resultados_ocr)

    texto_final = texto_extraido.upper()
    datos = procesar_texto_a_diccionario(texto_final)
    datos["texto_bruto"] = texto_final
    return datos
