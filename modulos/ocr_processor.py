import re
import fitz
import numpy as np


def procesar_texto_a_diccionario(texto):
    # Limpieza total y estandarización
    texto = " ".join(texto.split()).upper()

    # 1. Extraer todos los candidatos posibles usando patrones universales
    rfcs = re.findall(r"\b[A-Z&Ñ]{3,4}\d{6}[A-Z0-9]{3}\b", texto)
    curps = re.findall(
        r"\b[A-Z][AEIOUX][A-Z]{2}\d{6}[HM][A-Z]{2}[A-Z0-9]{3}\d\b", texto)
    codigos_postales = re.findall(r"\b\d{5}\b", texto)

    # 2. Función auxiliar para buscar valores después de una etiqueta
    def buscar_valor(etiqueta, patron_valor, texto_fuente):
        # Busca la etiqueta y captura lo que sigue hasta encontrar otra etiqueta o mucho espacio
        match = re.search(
            rf"{etiqueta}[:\s]*(.*?)(?=RFC:|CURP:|NOMBRE|PRIMER|SEGUNDO|FECHA|ESTATUS|CÓDIGO|TIPO|NÚMERO|$)", texto_fuente, re.IGNORECASE)
        if match:
            valor = match.group(1).strip()
            # Si el valor capturado es solo ruido o etiquetas pegadas, intentamos limpiar
            return valor
        return ""

    # 3. Mapeo inteligente
    resultados = {
        "RFC:": rfcs[0] if rfcs else "",
        "CURP:": curps[0] if curps else "",
        "Nombre (s):": buscar_valor("NOMBRE \(S\)", r".*", texto),
        "Primer Apellido:": buscar_valor("PRIMER APELLIDO", r".*", texto),
        "Segundo Apellido:": buscar_valor("SEGUNDO APELLIDO", r".*", texto),
        "Código Postal:": codigos_postales[0] if codigos_postales else "",
        "Tipo de Vialidad:": buscar_valor("TIPO DE VIALIDAD", r".*", texto),
        "Nombre de Vialidad:": buscar_valor("NOMBRE DE VIALIDAD", r".*", texto),
        "Número Exterior:": buscar_valor("NÚMERO EXTERIOR", r".*", texto),
        "Número Interior:": buscar_valor("NÚMERO INTERIOR", r".*", texto),
        "Nombre de Colonia:": buscar_valor("NOMBRE DE (?:LA )?COLONIA", r".*", texto),
        "Nombre de la Localidad:": buscar_valor("NOMBRE DE LA LOCALIDAD", r".*", texto),
        "Nombre de Municipio o Demarcación Territorial:": buscar_valor("MUNICIPIO O DEMARCACIÓN TERRITORIAL", r".*", texto),
        "Nombre de la Entidad Federativa:": buscar_valor("ENTIDAD FEDERATIVA", r".*", texto)
    }

    # Lógica de respaldo: Si el nombre sigue vacío por el formato "no lineal",
    # buscamos el bloque de texto que usualmente sigue a los RFCs/CURPs
    if not resultados["Nombre (s):"] and len(rfcs) > 0:
        # Buscamos palabras grandes después del segundo o tercer RFC detectado
        palabras = texto.split()
        for i, word in enumerate(palabras):
            if word == rfcs[0] and i + 2 < len(palabras):
                # Probablemente lo que sigue es el nombre
                resultados["Nombre (s):"] = palabras[i+1]
                break

    return resultados


def extraer_datos_memoria(file_bytes, is_pdf=True):
    texto_extraido = ""
    if is_pdf:
        try:
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            for pagina in doc:
                # Cambiamos a "words" para forzar un orden de lectura de izquierda a derecha y arriba abajo
                words = pagina.get_text("words")
                texto_extraido += " ".join([w[4] for w in words]) + " "
            doc.close()
        except Exception as e:
            print(f"Error: {e}")

    texto_limpio = " ".join(texto_extraido.split()).upper()
    resultados = procesar_texto_a_diccionario(texto_limpio)
    resultados["texto_bruto"] = texto_limpio
    return resultados
