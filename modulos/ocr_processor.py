import re
import fitz
import numpy as np
import cv2
import easyocr


def procesar_texto_a_diccionario(texto):
    # Limpieza total para facilitar la búsqueda
    texto = " ".join(texto.split()).upper()

    # 1. BÚSQUEDA POR ESTRUCTURA (Para cualquier formato de constancia)
    rfcs = re.findall(r"\b[A-ZÑ&]{3,4}\d{6}[A-Z0-9]{3}\b", texto)
    curps = re.findall(
        r"\b[A-Z][AEIOUX][A-Z]{2}\d{6}[HM][A-Z]{2}[A-Z0-9]{3}\d\b", texto)
    codigos_postales = re.findall(r"\b\d{5}\b", texto)

    # 2. BÚSQUEDA DE NOMBRE (Busca entre etiquetas clave)
    def extraer_nombre(texto_fuente):
        match = re.search(
            r"(?:CONTRIBUYENTE|SOCIAL)[:\s]+([A-Z\sÑÁÉÍÓÚ]{10,60})(?=\s+RFC|IDCIF|CURP|$)", texto_fuente)
        if match:
            nombre = match.group(1).strip()
            basura = ["REGISTRO", "FEDERAL",
                      "CONTRIBUYENTES", "DOMICILIO", "DATOS"]
            palabras = [p for p in nombre.split(
            ) if p not in basura and len(p) > 1]
            return palabras
        return []

    partes_nombre = extraer_nombre(texto)

    # 3. BÚSQUEDA DE DIRECCIÓN (Lógica de "frenos" entre etiquetas)
    def buscar_entre(inicio, fin, fuente):
        patron = rf"{inicio}[:\s]*([A-Z0-9\sÑÁÉÍÓÚ\.\-\/]+?)(?=\s+{fin}|PÁGINA|$)"
        m = re.search(patron, fuente)
        return m.group(1).strip() if m else ""

    return {
        "RFC:": rfcs[0] if rfcs else "",
        "CURP:": curps[0] if curps else "",
        "Nombre (s):": " ".join(partes_nombre[:2]) if len(partes_nombre) >= 2 else (partes_nombre[0] if partes_nombre else ""),
        "Primer Apellido:": partes_nombre[-2] if len(partes_nombre) >= 3 else (partes_nombre[1] if len(partes_nombre) == 2 else ""),
        "Segundo Apellido:": partes_nombre[-1] if len(partes_nombre) >= 4 else "",
        "Código Postal:": codigos_postales[0] if codigos_postales else "",
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
            print(f"Error PDF: {e}")

    # OCR de respaldo si el PDF es imagen o viene vacío
    if len(texto_extraido) < 50:
        try:
            reader = easyocr.Reader(['es'])
            nparr = np.frombuffer(file_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            resultados_ocr = reader.readtext(img, detail=0)
            texto_extraido = " ".join(resultados_ocr)
        except Exception as e:
            print(f"Error OCR: {e}")

    texto_final = texto_extraido.upper()
    datos = procesar_texto_a_diccionario(texto_final)
    datos["texto_bruto"] = texto_final
    return datos
