import re
import fitz
import numpy as np
import cv2
import easyocr


def procesar_texto_a_diccionario(texto):
    # 1. Normalización total: un solo espacio y todo a mayúsculas
    texto = " ".join(texto.split()).upper()

    # 2. Lista de etiquetas que ensucian la extracción (Basura del SAT)
    basura = [
        r"NOMBRE\s*\(S\)", r"PRIMER\s+APELLIDO", r"SEGUNDO\s+APELLIDO",
        r"CURP", r"RFC", r"CÉDULA\s+DE\s+IDENTIFICACIÓN\s+FISCAL",
        r"CONSTANCIA\s+DE\s+SITUACIÓN\s+FISCAL", r"DATOS\s+DE\s+IDENTIFICACIÓN",
        r"REGISTRO\s+FEDERAL\s+DE\s+CONTRIBUYENTES"
    ]

    # Función para limpiar etiquetas del valor extraído
    def limpiar_valor(v):
        for b in basura:
            v = re.sub(b, "", v)
        return v.strip(" :. -")

    # 3. Función de extracción con "Stop Words" (Frenos)
    def buscar_campo(etiqueta, frenos, fuente):
        # Busca la etiqueta y captura hasta encontrar el siguiente campo o el final
        patron = rf"{etiqueta}[:\s]+(.*?)(?=\s+(?:{frenos}|PÁGINA|$))"
        match = re.search(patron, fuente)
        if match:
            return limpiar_valor(match.group(1))
        return ""

    # 4. Mapeo por patrones fuertes (RFC, CURP, CP)
    rfcs = re.findall(r"\b[A-ZÑ&]{3,4}\d{6}[A-Z0-9]{3}\b", texto)
    curps = re.findall(
        r"\b[A-Z][AEIOUX][A-Z]{2}\d{6}[HM][A-Z]{2}[A-Z0-9]{3}\d\b", texto)
    cps = re.findall(r"\b\d{5}\b", texto)

    return {
        "RFC:": rfcs[0] if rfcs else "",
        "CURP:": curps[0] if curps else "",
        "Nombre (s):": buscar_campo(r"NOMBRE\s*\(S\)", "PRIMER APELLIDO|RFC", texto),
        "Primer Apellido:": buscar_campo("PRIMER APELLIDO", "SEGUNDO APELLIDO|RFC", texto),
        "Segundo Apellido:": buscar_campo("SEGUNDO APELLIDO", "FECHA|ESTATUS|CURP", texto),
        "Código Postal:": cps[0] if cps else "",
        "Tipo de Vialidad:": buscar_campo("TIPO DE VIALIDAD", "NOMBRE DE VIALIDAD", texto),
        "Nombre de Vialidad:": buscar_campo("NOMBRE DE VIALIDAD", "NÚMERO EXTERIOR", texto),
        "Número Exterior:": buscar_campo("NÚMERO EXTERIOR", "NÚMERO INTERIOR", texto),
        "Número Interior:": buscar_campo("NÚMERO INTERIOR", "NOMBRE DE (?:LA )?COLONIA", texto),
        "Nombre de la Colonia:": buscar_campo("NOMBRE DE (?:LA )?COLONIA", "NOMBRE DE (?:LA )?LOCALIDAD", texto),
        "Nombre de la Localidad:": buscar_campo("NOMBRE DE (?:LA )?LOCALIDAD", "NOMBRE DE MUNICIPIO", texto),
        "Nombre del Municipio o Demarcación Territorial:": buscar_campo("TERRITORIAL", "NOMBRE DE (?:LA )?ENTIDAD", texto),
        "Nombre de la Entidad Federativa:": buscar_campo("ENTIDAD FEDERATIVA", "ENTRE CALLE|ENTRE LAS CALLES", texto),
        "Entre Calle:": buscar_campo("ENTRE CALLE", "Y CALLE|ACTIVIDADES", texto)
    }


def extraer_datos_memoria(file_bytes, is_pdf=True):
    texto_final = ""
    if is_pdf:
        try:
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            for pagina in doc:
                # Extraemos el texto en orden físico (top-to-bottom)
                texto_final += pagina.get_text("text", sort=True) + " "
            doc.close()
        except:
            pass

    # Si el texto es basura o imagen, aplicamos OCR
    if len(texto_final.strip()) < 60:
        reader = easyocr.Reader(['es'])
        img = cv2.imdecode(np.frombuffer(
            file_bytes, np.uint8), cv2.IMREAD_COLOR)
        texto_final = " ".join(reader.readtext(img, detail=0))

    return procesar_texto_a_diccionario(texto_final.upper())
