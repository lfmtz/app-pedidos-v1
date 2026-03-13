import re
import fitz
import numpy as np
import cv2
import easyocr


def procesar_texto_a_diccionario(texto):
    # 1. Normalización: Quitamos ruidos comunes del PDF
    texto = " ".join(texto.split()).upper()

    # 2. Diccionario de resultados vacío
    res = {k: "" for k in [
        "RFC:", "CURP:", "Nombre (s):", "Primer Apellido:", "Segundo Apellido:",
        "Código Postal:", "Tipo de Vialidad:", "Nombre de Vialidad:",
        "Número Exterior:", "Número Interior:", "Nombre de la Colonia:",
        "Nombre de la Localidad:", "Nombre del Municipio o Demarcación Territorial:",
        "Nombre de la Entidad Federativa:", "Entre Calle:"
    ]}

    # --- EXTRACCIÓN POR PATRONES (RFC, CURP, CP son únicos) ---
    rfcs = re.findall(r"\b[A-ZÑ&]{3,4}\d{6}[A-Z0-9]{3}\b", texto)
    curps = re.findall(
        r"\b[A-Z][AEIOUX][A-Z]{2}\d{6}[HM][A-Z]{2}[A-Z0-9]{3}\d\b", texto)
    cps = re.findall(r"\b\d{5}\b", texto)

    if rfcs:
        res["RFC:"] = rfcs[0]
    if curps:
        res["CURP:"] = curps[0]
    if cps:
        res["Código Postal:"] = cps[0]

    # --- LÓGICA DE EXTRACCIÓN DINÁMICA (Búsqueda entre anclas) ---
    def extraer(ancla_inicio, ancla_fin, fuente):
        # Busca lo que esté entre dos etiquetas, sin importar cuántos espacios haya
        patron = rf"{ancla_inicio}[:\s]+(.*?)(?=\s+{ancla_fin}|PÁGINA|$)"
        match = re.search(patron, fuente)
        if match:
            valor = match.group(1).strip()
            # Si el valor capturado contiene otras etiquetas, está sucio
            if ":" in valor or len(valor) < 1:
                return ""
            return valor
        return ""

    # Asignación dinámica basada en las etiquetas estándar del SAT
    res["Nombre (s):"] = extraer("NOMBRE\s*\(S\)", "PRIMER APELLIDO", texto)
    res["Primer Apellido:"] = extraer(
        "PRIMER APELLIDO", "SEGUNDO APELLIDO", texto)
    res["Segundo Apellido:"] = extraer(
        "SEGUNDO APELLIDO", "FECHA INICIO|CURP", texto)
    res["Tipo de Vialidad:"] = extraer(
        "TIPO DE VIALIDAD", "NOMBRE DE VIALIDAD", texto)
    res["Nombre de Vialidad:"] = extraer(
        "NOMBRE DE VIALIDAD", "NÚMERO EXTERIOR", texto)
    res["Número Exterior:"] = extraer(
        "NÚMERO EXTERIOR", "NÚMERO INTERIOR", texto)
    res["Número Interior:"] = extraer(
        "NÚMERO INTERIOR", "NOMBRE DE (?:LA )?COLONIA", texto)
    res["Nombre de la Colonia:"] = extraer(
        "NOMBRE DE (?:LA )?COLONIA", "NOMBRE DE (?:LA )?LOCALIDAD", texto)
    res["Nombre de la Localidad:"] = extraer(
        "NOMBRE DE (?:LA )?LOCALIDAD", "NOMBRE DE MUNICIPIO", texto)
    res["Nombre del Municipio o Demarcación Territorial:"] = extraer(
        "TERRITORIAL", "NOMBRE DE (?:LA )?ENTIDAD", texto)
    res["Nombre de la Entidad Federativa:"] = extraer(
        "ENTIDAD FEDERATIVA", "ENTRE CALLE", texto)
    res["Entre Calle:"] = extraer("ENTRE CALLE", "Y CALLE", texto)

    return res


def extraer_datos_memoria(file_bytes, is_pdf=True):
    texto_acumulado = ""
    if is_pdf:
        try:
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            for pagina in doc:
                # El modo "dict" nos da la posición exacta de cada palabra
                blocks = pagina.get_text("dict")["blocks"]
                for b in blocks:
                    if "lines" in b:
                        for l in b["lines"]:
                            for s in l["spans"]:
                                texto_acumulado += s["text"] + " "
            doc.close()
        except:
            pass

    # Si el PDF es una imagen o falló la extracción de texto (OCR al rescate)
    if len(texto_acumulado.strip()) < 50:
        reader = easyocr.Reader(['es'])
        img = cv2.imdecode(np.frombuffer(
            file_bytes, np.uint8), cv2.IMREAD_COLOR)
        texto_acumulado = " ".join(reader.readtext(img, detail=0))

    return procesar_texto_a_diccionario(texto_acumulado.upper())
