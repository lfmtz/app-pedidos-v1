import re
import fitz


def procesar_texto_a_diccionario(texto):
    # Unificamos todo el texto en una sola línea limpia
    texto = " ".join(texto.split()).upper()

    # --- 1. IDENTIFICADORES (PATRONES FIJOS) ---
    rfcs = re.findall(r"\b[A-ZÑ&]{3,4}\d{6}[A-Z0-9]{3}\b", texto)
    curps = re.findall(
        r"\b[A-Z][AEIOUX][A-Z]{2}\d{6}[HM][A-Z]{2}[A-Z0-9]{3}\d\b", texto)
    cp = re.findall(r"\b\d{5}\b", texto)

    # --- 2. EXTRACCIÓN DEL NOMBRE (SIN ETIQUETAS BASURA) ---
    nombre_completo = ""
    # El nombre real está entre 'RAZÓN SOCIAL:' e 'IDCIF' o entre 'CONTRIBUYENTE:' y 'RFC:'
    m1 = re.search(r"SOCIAL[:\s]+([A-Z\sÑÁÉÍÓÚ]+?)(?=\s+IDCIF|RFC:|$)", texto)
    m2 = re.search(r"CONTRIBUYENTE[:\s]+([A-Z\sÑÁÉÍÓÚ]+?)(?=\s+RFC:|$)", texto)

    cand = m1.group(1).strip() if m1 else (m2.group(1).strip() if m2 else "")

    # Limpiamos palabras que no son nombres
    basura = ["REGISTRO", "FEDERAL", "CONTRIBUYENTES",
              "DATOS", "IDENTIFICACIÓN", "DOMICILIO"]
    palabras = [p for p in cand.split() if p not in basura and len(p) > 1]

    # Martha Vianey Delgado Cuevas -> N: Martha Vianey, P: Delgado, S: Cuevas
    res_n = " ".join(palabras[:2]) if len(
        palabras) >= 2 else (palabras[0] if palabras else "")
    res_p = palabras[-2] if len(palabras) >= 3 else (palabras[1]
                                                     if len(palabras) == 2 else "")
    res_m = palabras[-1] if len(palabras) >= 4 else ""

    # --- 3. DIRECCIÓN CON FRENOS DE SEGURIDAD ---
    def extraer(inicio, fin, fuente):
        pattern = rf"{inicio}[:\s]*([A-Z0-9\sÑÁÉÍÓÚ\.\-\/]+?)(?=\s+{fin}|\s+PÁGINA|$)"
        m = re.search(pattern, fuente)
        return m.group(1).strip() if m else ""

    return {
        "RFC:": rfcs[0] if rfcs else "",
        "CURP:": curps[0] if curps else "",
        "Nombre (s):": res_n,
        "Primer Apellido:": res_p,
        "Segundo Apellido:": res_m,
        "Código Postal:": cp[0] if cp else "",
        "Tipo de Vialidad:": extraer("TIPO DE VIALIDAD", "NOMBRE DE VIALIDAD", texto),
        "Nombre de Vialidad:": extraer("NOMBRE DE VIALIDAD", "NÚMERO EXTERIOR", texto),
        "Número Exterior:": extraer("NÚMERO EXTERIOR", "NÚMERO INTERIOR", texto),
        "Número Interior:": extraer("NÚMERO INTERIOR", "NOMBRE DE COLONIA", texto),
        "Nombre de Colonia:": extraer("NOMBRE DE COLONIA", "NOMBRE DE LA LOCALIDAD", texto),
        "Nombre de la Localidad:": extraer("NOMBRE DE LA LOCALIDAD", "NOMBRE DE MUNICIPIO", texto),
        "Nombre de Municipio o Demarcación Territorial:": extraer("TERRITORIAL", "NOMBRE DE LA ENTIDAD", texto),
        "Nombre de la Entidad Federativa:": extraer("ENTIDAD FEDERATIVA", "ENTRE CALLE", texto)
    }


def extraer_datos_memoria(file_bytes, is_pdf=True):
    texto_extraido = ""
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        for pagina in doc:
            texto_extraido += pagina.get_text("text") + " "
        doc.close()
    except Exception as e:
        print(f"Error: {e}")

    texto_limpio = " ".join(texto_extraido.split()).upper()
    resultados = procesar_texto_a_diccionario(texto_limpio)
    resultados["texto_bruto"] = texto_limpio
    return resultados
