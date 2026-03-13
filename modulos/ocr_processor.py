import re
import fitz


def procesar_texto_a_diccionario(file_stream):
    doc = fitz.open(stream=file_stream, filetype="pdf")
    # Extraemos el texto respetando el orden de las palabras en la hoja
    texto = " ".join(doc[0].get_text("text", sort=True).split()).upper()
    doc.close()

    # Función ultra-precisa: busca la etiqueta con sus ":" y corta en la siguiente
    def extraer_por_dos_puntos(etiqueta_con_puntos, etiqueta_freno):
        # Escapamos paréntesis para NOMBRE (S):
        etiqueta_escrita = etiqueta_con_puntos.replace(
            "(", "\(").replace(")", "\)")

        # Patrón: Busca 'ETIQUETA:' -> captura todo hasta la 'SIGUIENTE ETIQUETA'
        patron = rf"{etiqueta_escrita}\s*(.*?)(?=\s+{etiqueta_freno}|$)"
        match = re.search(patron, texto)

        if match:
            valor = match.group(1).strip()
            # Si se coló otro ":" por error del PDF, cortamos ahí
            return valor.split(":")[0].strip()
        return ""

    # --- TEST DE IDENTIDAD ---
    # Para RFC y CURP usamos patrones porque a veces el ":" no viene pegado
    rfc_match = re.search(r"\b[A-ZÑ&]{3,4}\d{6}[A-Z0-9]{3}\b", texto)
    curp_match = re.search(
        r"\b[A-Z][AEIOUX][A-Z]{2}\d{6}[HM][A-Z]{2}[A-Z0-9]{3}\d\b", texto)

    return {
        "RFC:": rfc_match.group(0) if rfc_match else "",
        "CURP:": curp_match.group(0) if curp_match else "",
        "Nombre (s):": extraer_por_dos_puntos("NOMBRE (S):", "PRIMER APELLIDO"),
        "Primer Apellido:": extraer_por_dos_puntos("PRIMER APELLIDO:", "SEGUNDO APELLIDO"),
        "Segundo Apellido:": extraer_por_dos_puntos("SEGUNDO APELLIDO:", "FECHA INICIO|ESTATUS|CURP")
    }


def extraer_datos_memoria(file_bytes, is_pdf=True):
    return procesar_texto_a_diccionario(file_bytes)
