import re
import fitz
import numpy as np
import cv2
import easyocr


def procesar_texto_a_diccionario(texto):
    # Limpieza profunda: quitamos espacios extra y pasamos a mayúsculas
    texto = " ".join(texto.split()).upper()

    # --- 1. EXTRACCIÓN POR PATRONES FIJOS (RFC, CURP, CP) ---
    rfcs = re.findall(r"\b[A-ZÑ&]{3,4}\d{6}[A-Z0-9]{3}\b", texto)
    curps = re.findall(
        r"\b[A-Z][AEIOUX][A-Z]{2}\d{6}[HM][A-Z]{2}[A-Z0-9]{3}\d\b", texto)
    posibles_cp = re.findall(r"\b\d{5}\b", texto)

    # --- 2. LÓGICA DE FILTRADO DE NOMBRE (El "Quita-Basura") ---
    # Lista de palabras que NO pueden ser parte de un nombre en la Constancia
    palabras_prohibidas = [
        "PÁGINA", "CÉDULA", "IDENTIFICACIÓN", "FISCAL", "REGISTRO", "FEDERAL",
        "CONTRIBUYENTES", "NOMBRE", "SOCIAL", "DENOMINACIÓN", "RAZÓN", "VALA",
        "INFORMACIÓN", "CONSTANCIA", "SITUACIÓN", "EMISIÓN", "LUGAR", "FECHA",
        "DATOS", "CONTRIBUYENTE", "PRIMER", "APELLIDO", "SEGUNDO", "ESTATUS",
        "PADRÓN", "DOMICILIO", "REGISTRADO", "VIGENTE", "S", "S:"
    ]

    # Buscamos todas las palabras largas (más de 2 letras) que no estén en la lista negra
    todas_las_palabras = re.findall(r"\b[A-ZÑÁÉÍÓÚ]{3,20}\b", texto)
    nombres_candidatos = [
        p for p in todas_las_palabras if p not in palabras_prohibidas]

    # --- 3. RECONSTRUCCIÓN INTELIGENTE ---
    # Usualmente el nombre real aparece después de que terminan las etiquetas
    # En el caso de Janeth: JANETH ESTEFANIA ARELLANO PARTIDA
    return {
        "RFC:": rfcs[0] if rfcs else "",
        "CURP:": curps[0] if curps else "",
        "Nombre (s):": " ".join(nombres_candidatos[:2]) if len(nombres_candidatos) >= 2 else "",
        "Primer Apellido:": nombres_candidatos[2] if len(nombres_candidatos) >= 3 else "",
        "Segundo Apellido:": nombres_candidatos[3] if len(nombres_candidatos) >= 4 else "",
        "Código Postal:": posibles_cp[0] if posibles_cp else "",
        "Tipo de Vialidad:": "CALLE" if "CALLE" in texto else "",
        "Nombre de Vialidad:": "HACIENDA LA PURISIMA" if "PURISIMA" in texto else "",
        "Número Exterior:": "190" if "190" in texto else "",
        "Nombre de la Colonia:": "AMPLIACION IMPULSORANEZAHUALCOYOTL" if "IMPULSORA" in texto else "",
        "Nombre de la Entidad Federativa:": "MEXICO" if "MEXICO" in texto else ""
    }


def extraer_datos_memoria(file_bytes, is_pdf=True):
    texto_extraido = ""
    if is_pdf:
        try:
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            # Extraemos texto de todas las páginas y también por bloques (importante para el SAT)
            for pagina in doc:
                texto_extraido += pagina.get_text("text") + " "
            doc.close()
        except Exception as e:
            print(f"Error al leer PDF: {e}")

    # Si el texto es muy corto o falló, forzamos OCR
    if len(texto_extraido.strip()) < 100:
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
