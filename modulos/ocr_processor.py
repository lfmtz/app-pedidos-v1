import re
import fitz


def procesar_texto_a_diccionario(texto):
    # Unificamos todo el texto en una sola línea para que sea fácil de leer
    texto = " ".join(texto.split()).upper()

    # Diccionario de búsqueda con patrones elásticos
    # Explicación: busca la etiqueta y captura lo que sigue hasta encontrar la SIGUIENTE etiqueta lógica
    patterns = {
        "RFC:": r"RFC:\s*([A-Z0-9]{12,13})",
        "CURP:": r"CURP:\s*([A-Z0-9]{18})",
        "Nombre (s):": r"NOMBRE\s*\(S\):\s*([A-Z\sÑÁÉÍÓÚ]+?)(?=\s*PRIMER|APELLIDO|FECHA|$)",
        "Primer Apellido:": r"PRIMER\s*APELLIDO:\s*([A-Z\sÑÁÉÍÓÚ]+?)(?=\s*SEGUNDO|FECHA|$)",
        "Segundo Apellido:": r"SEGUNDO\s*APELLIDO:\s*([A-Z\sÑÁÉÍÓÚ]+?)(?=\s*FECHA|ESTATUS|$)",
        "Código Postal:": r"CÓDIGO\s*POSTAL:\s*(\d{5})",
        "Tipo de Vialidad:": r"TIPO\s*DE\s*VIALIDAD:\s*([A-Z\sÑÁÉÍÓÚ]+?)(?=\s*NOMBRE|NÚMERO|$)",
        "Nombre de Vialidad:": r"NOMBRE\s*DE\s*VIALIDAD:\s*([A-Z0-9\sÑÁÉÍÓÚ]+?)(?=\s*NÚMERO|NOMBRE|$)",
        "Número Exterior:": r"NÚMERO\s*EXTERIOR:\s*([A-Z0-9\s.-]+?)(?=\s*NÚMERO|NOMBRE|$)",
        "Número Interior:": r"NÚMERO\s*INTERIOR:\s*([A-Z0-9\s.-]+?)(?=\s*NOMBRE|COLONIA|$)",
        "Nombre de Colonia:": r"NOMBRE\s*DE\s*COLONIA:\s*([A-Z0-9\sÑÁÉÍÓÚ]+?)(?=\s*NOMBRE|LOCALIDAD|$)",
        "Nombre de la Localidad:": r"NOMBRE\s*DE\s*LA\s*LOCALIDAD:\s*([A-Z\sÑÁÉÍÓÚ]+?)(?=\s*NOMBRE|MUNICIPIO|$)",
        "Nombre de Municipio o Demarcación Territorial:": r"MUNICIPIO\s*O\s*DEMARCACIÓN\s*TERRITORIAL:\s*([A-Z\sÑÁÉÍÓÚ]+?)(?=\s*NOMBRE|ENTIDAD|$)",
        "Nombre de la Entidad Federativa:": r"ENTIDAD\s*FEDERATIVA:\s*([A-Z\sÑÁÉÍÓÚ]+?)(?=\s*ENTRE|CALLE|$)"
    }

    resultados = {}
    for campo, ptr in patterns.items():
        match = re.search(ptr, texto, re.IGNORECASE)
        if match:
            # Limpieza: quitamos espacios extra y limitamos longitud para no traer basura
            valor = match.group(1).strip()
            # Si el valor capturado contiene palabras clave de etiquetas, es que leyó mal
            if any(x in valor for x in ["NOMBRE", "NÚMERO", "PÁGINA"]):
                resultados[campo] = ""
            else:
                resultados[campo] = valor
        else:
            resultados[campo] = ""

    return resultados


def extraer_datos_memoria(file_bytes, is_pdf=True):
    texto_extraido = ""
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        for pagina in doc:
            # "text" es el modo más fiel para este tipo de PDFs
            texto_extraido += pagina.get_text("text") + " "
        doc.close()
    except Exception as e:
        print(f"Error: {e}")

    texto_limpio = " ".join(texto_extraido.split()).upper()
    resultados = procesar_texto_a_diccionario(texto_limpio)
    resultados["texto_bruto"] = texto_limpio
    return resultados
