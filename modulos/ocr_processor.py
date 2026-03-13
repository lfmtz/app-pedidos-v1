import re
import fitz


def procesar_texto_a_diccionario(file_stream):
    doc = fitz.open(stream=file_stream, filetype="pdf")
    pagina = doc[0]

    # Extraemos el texto respetando la estructura visual de bloques
    texto_sucio = pagina.get_text("text", sort=True).upper()

    # Definimos el mapa de correspondencia: {Etiqueta en PDF: Campo en App}
    mapa_campos = {
        "RFC": "RFC:",
        "CURP": "CURP:",
        "NOMBRE (S)": "Nombre (s):",
        "PRIMER APELLIDO": "Primer Apellido:",
        "SEGUNDO APELLIDO": "Segundo Apellido:",
        "CÓDIGO POSTAL": "Código Postal:",
        "TIPO DE VIALIDAD": "Tipo de Vialidad:",
        "NOMBRE DE VIALIDAD": "Nombre de Vialidad:",
        "NÚMERO EXTERIOR": "Número Exterior:",
        "NÚMERO INTERIOR": "Número Interior:",
        "NOMBRE DE LA COLONIA": "Nombre de la Colonia:",
        "NOMBRE DE LA LOCALIDAD": "Nombre de la Localidad:",
        "MUNICIPIO": "Nombre del Municipio o Demarcación Territorial:",
        "ENTIDAD FEDERATIVA": "Nombre de la Entidad Federativa:"
    }

    # Orden de las etiquetas según aparecen normalmente en el SAT para poner "frenos"
    orden_etiquetas = list(mapa_campos.keys())
    res = {v: "" for v in mapa_campos.values()}

    for i, etiqueta in enumerate(orden_etiquetas):
        # El "freno" es la siguiente etiqueta en la lista para no pasarnos de largo
        freno = orden_etiquetas[i+1] if i + \
            1 < len(orden_etiquetas) else "PÁGINA|FECHA|ESTATUS"

        # Regex: Busca la ETIQUETA, ignora los : y espacios, captura hasta el FRENO
        # El [\(S\)]* es para que coincida con "NOMBRE (S)" o solo "NOMBRE"
        patron = rf"{etiqueta}.*?[:\s]+(.*?)(?=\s+{freno}|$)"
        match = re.search(patron, texto_sucio, re.DOTALL)

        if match:
            valor = match.group(1).strip()
            # Limpieza final: si por error se coló la misma etiqueta o los ":"
            valor = valor.replace(etiqueta, "").strip(" :.-")

            # Asignamos al campo correspondiente de la App
            campo_app = mapa_campos[etiqueta]
            res[campo_app] = valor

    doc.close()
    return res


def extraer_datos_memoria(file_bytes, is_pdf=True):
    return procesar_texto_a_diccionario(file_bytes)
