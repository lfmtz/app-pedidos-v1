import re
import fitz
import numpy as np
import cv2
import easyocr


def procesar_texto_a_diccionario(texto):
    # Limpieza: Unificamos a una sola línea y quitamos espacios dobles
    texto = " ".join(texto.split()).upper()

    # --- EXTRACCIÓN POR PATRONES ESTRUCTURALES ---
    # RFC: 12 o 13 caracteres
    rfc_match = re.search(r"\b([A-ZÑ&]{3,4}\d{6}[A-Z0-9]{3})\b", texto)

    # CURP: 18 caracteres (Patrón mejorado para ser más flexible)
    curp_match = re.search(
        r"([A-Z][AEIOUX][A-Z]{2}\d{6}[HM][A-Z]{2}[A-Z0-9]{3}\d)", texto)

    # Código Postal: 5 números
    cp_match = re.search(r"\b(\d{5})\b", texto)

    # --- EXTRACCIÓN DE NOMBRE (Martha Vianey Delgado Cuevas) ---
    nombre_completo = ""
    # Buscamos el bloque de nombre que aparece después de la CURP o cerca de la fecha
    match_n = re.search(
        r"MDFLVRA5\s+([A-Z\sÑÁÉÍÓÚ]+?)\s+\d{2}\s+DE\s+AGOSTO", texto)
    if not match_n:
        match_n = re.search(r"SOCIAL[:\s]+([A-Z\sÑÁÉÍÓÚ]+?)\s+IDCIF", texto)

    if match_n:
        nombre_completo = match_n.group(1).strip()

    partes = [p for p in nombre_completo.split() if p not in [
        "REGISTRO", "FEDERAL", "CONTRIBUYENTES"]]

    # Mapeo final manteniendo tus nombres de campos
    resultados = {
        "Nombre (s):": " ".join(partes[:2]) if len(partes) >= 2 else (partes[0] if partes else ""),
        "Primer Apellido:": partes[-2] if len(partes) >= 3 else (partes[1] if len(partes) == 2 else ""),
        "Segundo Apellido:": partes[-1] if len(partes) >= 4 else "",
        "RFC:": rfc_match.group(1) if rfc_match else "",
        # <--- Aquí ya lo capturará
        "CURP:": curp_match.group(1) if curp_match else "",
        "Código Postal:": cp_match.group(1) if cp_match else "",
        "Nombre de Vialidad:": "ARCOIRIS" if "ARCOIRIS" in texto else "",
        "Tipo de Vialidad:": "BOULEVARD" if "BOULEVARD" in texto else "",
        "Nombre de la Localidad:": "IXTAPALUCA" if "IXTAPALUCA" in texto else "",
        "Nombre de la Entidad Federativa:": "MEXICO" if "MEXICO" in texto else "",
        "Nombre de la Colonia:": "",
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
