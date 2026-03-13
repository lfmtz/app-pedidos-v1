import re
import fitz
import numpy as np
import cv2
import easyocr


def procesar_texto_a_diccionario(texto):
    # 1. Normalización total del texto
    texto = " ".join(texto.split()).upper()

    # 2. Función de búsqueda dinámica mejorada
    def buscar_dinamico(etiqueta, frenos, fuente):
        # Esta regex busca la etiqueta y captura TODO hasta encontrar un "freno" (otra etiqueta)
        # o un límite de caracteres para evitar que se coma todo el documento
        patron = rf"{etiqueta}[:\s]*([\w\sÑÁÉÍÓÚ\.\-\/]+?)(?=\s+(?:{frenos}|PÁGINA|$))"
        match = re.search(patron, fuente)
        if match:
            valor = match.group(1).strip()
            # Si el valor capturado es solo otra etiqueta (limpieza de ruido)
            if any(f in valor for f in frenos.split('|')):
                return ""
            return valor
        return ""

    # 3. Mapeo Dinámico (Sin datos fijos)
    rfcs = re.findall(r"\b[A-ZÑ&]{3,4}\d{6}[A-Z0-9]{3}\b", texto)
    curps = re.findall(
        r"\b[A-Z][AEIOUX][A-Z]{2}\d{6}[HM][A-Z]{2}[A-Z0-9]{3}\d\b", texto)
    cps = re.findall(r"\b\d{5}\b", texto)

    # Definimos los "frenos" (la siguiente etiqueta lógica) para cada campo
    res = {
        "RFC:": rfcs[0] if rfcs else "",
        "CURP:": curps[0] if curps else "",
        "Nombre (s):": buscar_dinamico("NOMBRE\s*\(.*?\)s", "PRIMER APELLIDO|RFC", texto),
        "Primer Apellido:": buscar_dinamico("PRIMER APELLIDO", "SEGUNDO APELLIDO|RFC", texto),
        "Segundo Apellido:": buscar_dinamico("SEGUNDO APELLIDO", "FECHA|ESTATUS|CURP", texto),
        "Código Postal:": cps[0] if cps else "",
        "Tipo de Vialidad:": buscar_dinamico("TIPO DE VIALIDAD", "NOMBRE DE VIALIDAD", texto),
        "Nombre de Vialidad:": buscar_dinamico("NOMBRE DE VIALIDAD", "NÚMERO EXTERIOR", texto),
        "Número Exterior:": buscar_dinamico("NÚMERO EXTERIOR", "NÚMERO INTERIOR", texto),
        "Número Interior:": buscar_dinamico("NÚMERO INTERIOR", "NOMBRE DE (?:LA )?COLONIA", texto),
        "Nombre de la Colonia:": buscar_dinamico("NOMBRE DE (?:LA )?COLONIA", "NOMBRE DE (?:LA )?LOCALIDAD", texto),
        "Nombre de la Localidad:": buscar_dinamico("NOMBRE DE (?:LA )?LOCALIDAD", "NOMBRE DE MUNICIPIO", texto),
        "Nombre del Municipio o Demarcación Territorial:": buscar_dinamico("TERRITORIAL", "NOMBRE DE (?:LA )?ENTIDAD", texto),
        "Nombre de la Entidad Federativa:": buscar_dinamico("ENTIDAD FEDERATIVA", "ENTRE CALLE|ENTRE LAS CALLES", texto)
    }

    return res


def extraer_datos_memoria(file_bytes, is_pdf=True):
    texto_extraido = ""
    if is_pdf:
        try:
            # Usamos el modo "blocks" para mantener la relación visual de los datos
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            for pagina in doc:
                bloques = pagina.get_text("blocks")
                # Ordenamos bloques de arriba a abajo para no perder el orden de los datos
                bloques.sort(key=lambda b: (b[1], b[0]))
                for b in bloques:
                    texto_extraido += b[4] + " "
            doc.close()
        except Exception as e:
            print(f"Error: {e}")

    # Si el texto es nulo o imagen, EasyOCR entra al rescate
    if len(texto_extraido.strip()) < 50:
        reader = easyocr.Reader(['es'])
        img = cv2.imdecode(np.frombuffer(
            file_bytes, np.uint8), cv2.IMREAD_COLOR)
        texto_extraido = " ".join(reader.readtext(img, detail=0))

    return procesar_texto_a_diccionario(texto_extraido.upper())
