import re
import fitz
import numpy as np
import cv2
import easyocr


def procesar_texto_a_diccionario(texto):
    # Limpieza: unificamos a una sola línea para evitar saltos de línea molestos
    texto = " ".join(texto.split()).upper()

    # --- 1. EXTRACCIÓN POR ESTRUCTURA (Para cualquier PDF) ---
    # Buscamos el formato del dato, no solo la etiqueta
    rfcs = re.findall(r"\b[A-ZÑ&]{3,4}\d{6}[A-Z0-9]{3}\b", texto)
    curps = re.findall(
        r"\b[A-Z][AEIOUX][A-Z]{2}\d{6}[HM][A-Z]{2}[A-Z0-9]{3}\d\b", texto)
    cp = re.findall(r"\b\d{5}\b", texto)

    # --- 2. EXTRACCIÓN DEL NOMBRE ---
    def extraer_nombre(fuente):
        # Busca después de etiquetas comunes del SAT
        m = re.search(
            r"(?:CONTRIBUYENTE|SOCIAL)[:\s]+([A-Z\sÑÁÉÍÓÚ]{5,60})(?=\s+RFC|IDCIF|CURP|DATOS|$)", fuente)
        if m:
            nombre = m.group(1).strip()
            basura = ["REGISTRO", "FEDERAL",
                      "CONTRIBUYENTES", "DATOS", "IDENTIFICACIÓN"]
            palabras = [p for p in nombre.split(
            ) if p not in basura and len(p) > 1]
            return palabras
        return []

    partes = extraer_nombre(texto)

    # --- 3. EXTRACCIÓN DE DIRECCIÓN (Búsqueda entre etiquetas) ---
    def buscar_entre(inicio, fin, fuente):
        patron = rf"{inicio}[:\s]*([A-Z0-9\sÑÁÉÍÓÚ\.\-\/]+?)(?=\s+{fin}|PÁGINA|$)"
        m = re.search(patron, fuente)
        return m.group(1).strip() if m else ""

    return {
        "RFC:": rfcs[0] if rfcs else "",
        "CURP:": curps[0] if curps else "",
        "Nombre (s):": " ".join(partes[:2]) if len(partes) >= 2 else (partes[0] if partes else ""),
        "Primer Apellido:": partes[-2] if len(partes) >= 3 else (partes[1] if len(partes) == 2 else ""),
        "Segundo Apellido:": partes[-1] if len(partes) >= 4 else "",
        "Código Postal:": cp[0] if cp else "",
        "Tipo de Vialidad:": buscar_entre("TIPO DE VIALIDAD", "NOMBRE DE VIALIDAD", texto),
        "Nombre de Vialidad:": buscar_entre("NOMBRE DE VIALIDAD", "NÚMERO EXTERIOR", texto),
        "Número Exterior:": buscar_entre("NÚMERO EXTERIOR", "NÚMERO INTERIOR", texto),
        "Número Interior:": buscar_entre("NÚMERO INTERIOR", "NOMBRE DE (?:LA )?COLONIA", texto),
        "Nombre de la Colonia:": buscar_entre("NOMBRE DE (?:LA )?COLONIA", "NOMBRE DE (?:LA )?LOCALIDAD", texto),
        "Nombre de la Localidad:": buscar_entre("NOMBRE DE (?:LA )?LOCALIDAD", "NOMBRE DE MUNICIPIO", texto),
        "Nombre del Municipio o Demarcación Territorial:": buscar_entre("TERRITORIAL", "NOMBRE DE (?:LA )?ENTIDAD", texto),
        "Nombre de la Entidad Federativa:": buscar_entre("ENTIDAD FEDERATIVA", "ENTRE CALLE", texto)
    }


def extraer_datos_memoria(file_bytes, is_pdf=True):
    texto_extraido = ""
    if is_pdf:
        try:
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            for pagina in doc:
                texto_extraido += pagina.get_text() + " "
            doc.close()
        except Exception as e:
            print(f"Error al leer PDF: {e}")

    # Si el PDF está vacío o es imagen, usamos OCR
    if len(texto_extraido.strip()) < 50:
        try:
            reader = easyocr.Reader(['es'])
            nparr = np.frombuffer(file_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            resultados_ocr = reader.readtext(img, detail=0)
            texto_extraido = " ".join(resultados_ocr)
        except Exception as e:
            print(f"Error en OCR: {e}")

    texto_final = texto_extraido.upper()
    datos = procesar_texto_a_diccionario(texto_final)
    datos["texto_bruto"] = texto_final
    return datos
