import re
import fitz


def procesar_texto_a_diccionario(texto):
    # Limpiamos el texto y quitamos espacios extra
    texto = " ".join(texto.split()).upper()

    # --- 1. EXTRACCIÓN DE IDENTIFICADORES (POR PATRÓN LEGAL) ---
    rfcs = re.findall(r"\b[A-ZÑ&]{3,4}\d{6}[A-Z0-9]{3}\b", texto)
    curps = re.findall(
        r"\b[A-Z][AEIOUX][A-Z]{2}\d{6}[HM][A-Z]{2}[A-Z0-9]{3}\d\b", texto)
    codigos_postales = re.findall(r"\b\d{5}\b", texto)

    # --- 2. EXTRACCIÓN DEL NOMBRE (EL CORAZÓN DEL PROBLEMA) ---
    # En la constancia, el nombre real siempre aparece antes del RFC o después de 'CONTRIBUYENTE:'
    # Buscamos el bloque que NO contiene palabras como 'REGISTRO', 'FEDERAL' o 'FISCAL'
    nombre_completo = ""
    # Buscamos el texto que está entre 'CONTRIBUYENTE:' y 'RFC:'
    match_n = re.search(
        r"CONTRIBUYENTE[:\s]*([A-Z\sÑÁÉÍÓÚ]+?)(?=\s*RFC:)", texto)

    if not match_n:
        # Intento B: Nombre que aparece antes del primer RFC detectado
        if rfcs:
            primer_rfc = rfcs[0]
            # Buscamos texto en mayúsculas de al menos 3 palabras antes del RFC
            match_alt = re.search(
                rf"([A-Z\sÑÁÉÍÓÚ]{{10,60}})\s+{primer_rfc}", texto)
            if match_alt:
                nombre_completo = match_alt.group(1).strip()
    else:
        nombre_completo = match_n.group(1).strip()

    # Limpiamos el nombre de palabras basura del SAT
    basura = ["REGISTRO", "FEDERAL", "CONTRIBUYENTES",
              "DENOMINACIÓN", "RAZÓN", "SOCIAL", "DATOS"]
    for b in basura:
        nombre_completo = nombre_completo.replace(b, "").strip()

    # Dividimos nombre y apellidos (Asumiendo formato estándar)
    partes = nombre_completo.split()
    nombre = " ".join(
        partes[:-2]) if len(partes) > 2 else (partes[0] if partes else "")
    ap_paterno = partes[-2] if len(partes) >= 2 else ""
    ap_materno = partes[-1] if len(partes) >= 3 else ""

    # --- 3. EXTRACCIÓN DE DIRECCIÓN (POR DELIMITADORES) ---
    def extraer_campo(inicio, fin, fuente):
        pattern = rf"{inicio}[:\s]*([A-Z0-9\sÑÁÉÍÓÚ\.\(\)]+?)(?=\s*{fin}|$)"
        m = re.search(pattern, fuente)
        return m.group(1).strip() if m else ""

    resultados = {
        "RFC:": rfcs[0] if rfcs else "",
        "CURP:": curps[0] if curps else "",
        "Nombre (s):": nombre,
        "Primer Apellido:": ap_paterno,
        "Segundo Apellido:": ap_materno,
        "Código Postal:": codigos_postales[0] if codigos_postales else "",
        "Tipo de Vialidad:": extraer_campo("TIPO DE VIALIDAD", "NOMBRE DE VIALIDAD", texto),
        "Nombre de Vialidad:": extraer_campo("NOMBRE DE VIALIDAD", "NÚMERO EXTERIOR", texto),
        "Número Exterior:": extraer_campo("NÚMERO EXTERIOR", "NÚMERO INTERIOR", texto),
        "Número Interior:": extraer_campo("NÚMERO INTERIOR", "NOMBRE DE COLONIA", texto),
        "Nombre de Colonia:": extraer_campo("NOMBRE DE COLONIA", "NOMBRE DE LA LOCALIDAD", texto),
        "Nombre de la Localidad:": extraer_campo("NOMBRE DE LA LOCALIDAD", "NOMBRE DE MUNICIPIO", texto),
        "Nombre de Municipio o Demarcación Territorial:": extraer_campo("TERRITORIAL", "NOMBRE DE LA ENTIDAD", texto),
        "Nombre de la Entidad Federativa:": extraer_campo("ENTIDAD FEDERATIVA", "ENTRE CALLE", texto)
    }

    return resultados


def extraer_datos_memoria(file_bytes, is_pdf=True):
    texto_extraido = ""
    if is_pdf:
        try:
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            for pagina in doc:
                # Usamos 'blocks' para mantener la estructura visual del documento
                blocks = pagina.get_text("blocks")
                for b in blocks:
                    texto_extraido += b[4] + " "
            doc.close()
        except Exception as e:
            print(f"Error: {e}")

    texto_limpio = " ".join(texto_extraido.split()).upper()
    resultados = procesar_texto_a_diccionario(texto_limpio)
    resultados["texto_bruto"] = texto_limpio
    return resultados
