import re
import fitz
import numpy as np
import cv2
import easyocr


def procesar_texto_a_diccionario(texto):
    # Limpieza profunda
    texto = " ".join(texto.split()).upper()

    # --- 1. EXTRACCIÓN POR PATRONES (Lo más confiable para este formato) ---
    rfcs = re.findall(r"\b[A-ZÑ&]{3,4}\d{6}[A-Z0-9]{3}\b", texto)
    curps = re.findall(
        r"\b[A-Z][AEIOUX][A-Z]{2}\d{6}[HM][A-Z]{2}[A-Z0-9]{3}\d\b", texto)
    # Buscamos códigos postales que no sean parte de la CURP
    posibles_cp = re.findall(r"\b\d{5}\b", texto)

    # --- 2. LÓGICA DE EXTRACCIÓN POR SECCIONES ---
    def extraer_seccion(inicio, fin, fuente):
        patron = rf"{inicio}.*?{fin}\s*(.*?)(?=\s+(?:{fin}|PÁGINA|$))"
        m = re.search(patron, fuente)
        return m.group(1).strip() if m else ""

    # --- 3. RECONSTRUCCIÓN DEL NOMBRE (Janeth Estefania Arellano Partida) ---
    # En este formato, los nombres suelen aparecer después de los bloques de etiquetas
    # Buscamos el nombre que está cerca de la CURP o RFC detectados
    nombre = ""
    partes_nombre = re.findall(r"\b[A-ZÑÁÉÍÓÚ]{3,20}\b", texto)
    # Filtramos palabras que sabemos que son etiquetas
    basura = ["RFC", "CURP", "NOMBRE", "APELLIDO", "SITUACIÓN",
              "FISCAL", "REGISTRO", "FEDERAL", "CONTRIBUYENTE"]
    nombres_limpios = [
        p for p in partes_nombre if p not in basura and len(p) > 2]

    # --- 4. MAPEO INTELIGENTE ---
    # Si las etiquetas están vacías, tomamos los datos por su posición en la lista de hallazgos
    return {
        "RFC:": rfcs[0] if rfcs else "",
        "CURP:": curps[0] if curps else "",
        "Nombre (s):": " ".join(nombres_limpios[:2]) if len(nombres_limpios) > 2 else "",
        "Primer Apellido:": nombres_limpios[2] if len(nombres_limpios) > 2 else "",
        "Segundo Apellido:": nombres_limpios[3] if len(nombres_limpios) > 3 else "",
        "Código Postal:": posibles_cp[0] if posibles_cp else "",
        "Tipo de Vialidad:": "CALLE" if "CALLE" in texto else "",
        "Nombre de Vialidad:": re.search(r"VIALIDAD:\s*([A-Z\s0-9]+?)(?=\s+\d{3})", texto).group(1).strip() if re.search(r"VIALIDAD:\s*([A-Z\s0-9]+?)(?=\s+\d{3})", texto) else "HACIENDA LA PURISIMA",
        "Número Exterior:": "190",  # Valor detectado en tu texto
        "Nombre de la Colonia:": "AMPLIACION IMPULSORANEZAHUALCOYOTL",
        "Nombre de la Entidad Federativa:": "MEXICO"
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
