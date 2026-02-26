import re
import fitz


def procesar_texto_a_diccionario(texto):
    # Limpiamos el texto para que sea una sola línea plana
    texto = " ".join(texto.split()).upper()

    # 1. IDENTIFICADORES SEGUROS (Mantenemos la lógica que ya te funcionó)
    rfcs = re.findall(r"\b[A-ZÑ&]{3,4}\d{6}[A-Z0-9]{3}\b", texto)
    curps = re.findall(
        r"\b[A-Z][AEIOUX][A-Z]{2}\d{6}[HM][A-Z]{2}[A-Z0-9]{3}\d\b", texto)
    cp = re.findall(r"\b\d{5}\b", texto)

    # 2. CORRECCIÓN DE NOMBRE (Enfoque en Martha Vianey Delgado Cuevas)
    # Buscamos el bloque que está entre 'DENOMINACIÓN O RAZÓN SOCIAL:' y 'IDCIF'
    nombre_completo = ""
    match_nombre = re.search(
        r"SOCIAL[:\s]+([A-Z\sÑÁÉÍÓÚ]+?)(?=\s+IDCIF|RFC:|$)", texto)

    if match_nombre:
        nombre_completo = match_nombre.group(1).strip()

    # Si el nombre capturó "REGISTRO", lo buscamos en el bloque de abajo (Datos de Identificación)
    if "REGISTRO" in nombre_completo or len(nombre_completo) < 3:
        match_n2 = re.search(
            r"CONTRIBUYENTE[:\s]+([A-Z\sÑÁÉÍÓÚ]+?)(?=\s+RFC:|$)", texto)
        if match_n2:
            nombre_completo = match_n2.group(1).strip()

    # Dividir el nombre con seguridad
    partes = [p for p in nombre_completo.split() if p not in [
        "REGISTRO", "FEDERAL", "CONTRIBUYENTES"]]

    res_nombre = " ".join(partes[:2]) if len(
        partes) >= 2 else (partes[0] if partes else "")
    res_apellido_p = partes[-2] if len(partes) >= 3 else (
        partes[1] if len(partes) == 2 else "")
    res_apellido_m = partes[-1] if len(partes) >= 4 else ""

    # 3. DIRECCIÓN CON "FRENOS" PARA EVITAR PÁRRAFOS LARGOS
    def limpiar_campo(inicio, fin, texto_fuente):
        # El patrón busca el texto y se detiene en seco al encontrar la palabra 'fin'
        patron = rf"{inicio}[:\s]*([A-Z0-9\sÑÁÉÍÓÚ\.\-\/]+?)(?=\s+{fin}|\s+PÁGINA|$)"
        m = re.search(patron, texto_fuente)
        return m.group(1).strip() if m else ""

    resultados = {
        "RFC:": rfcs[0] if rfcs else "",
        "CURP:": curps[0] if curps else "",
        "Nombre (s):": res_nombre,
        "Primer Apellido:": res_apellido_p,
        "Segundo Apellido:": res_apellido_m,
        "Código Postal:": cp[0] if cp else "",
        "Tipo de Vialidad:": limpiar_campo("TIPO DE VIALIDAD", "NOMBRE DE VIALIDAD", texto),
        "Nombre de Vialidad:": limpiar_campo("NOMBRE DE VIALIDAD", "NÚMERO EXTERIOR", texto),
        "Número Exterior:": limpiar_campo("NÚMERO EXTERIOR", "NÚMERO INTERIOR", texto),
        "Número Interior:": limpiar_campo("NÚMERO INTERIOR", "NOMBRE DE COLONIA", texto),
        "Nombre de Colonia:": limpiar_campo("NOMBRE DE COLONIA", "NOMBRE DE LA LOCALIDAD", texto),
        "Nombre de la Localidad:": limpiar_campo("NOMBRE DE LA LOCALIDAD", "NOMBRE DE MUNICIPIO", texto),
        "Nombre de Municipio o Demarcación Territorial:": limpiar_campo("TERRITORIAL", "NOMBRE DE LA ENTIDAD", texto),
        "Nombre de la Entidad Federativa:": limpiar_campo("ENTIDAD FEDERATIVA", "ENTRE CALLE", texto)
    }

    return resultados
