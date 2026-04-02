def concatenar_nombre_cliente(datos):
    """
    Une nombres y apellidos buscando llaves con o sin dos puntos
    para ser compatible con OCR y Google Sheets.
    """
    # Buscamos nombres (Prueba 'Nombre (s):' y 'Nombre (s)')
    nombres = datos.get("Nombre (s):", datos.get("Nombre (s)", "")).strip()

    # Buscamos primer apellido (Prueba 'Primer Apellido:' y 'Primer Apellido')
    paterno = datos.get("Primer Apellido:", datos.get(
        "Primer Apellido", "")).strip()

    # Buscamos segundo apellido (Prueba 'Segundo Apellido:' y 'Segundo Apellido')
    materno = datos.get("Segundo Apellido:", datos.get(
        "Segundo Apellido", "")).strip()

    nombre_completo = f"{nombres} {paterno} {materno}".upper()

    # Limpia espacios dobles en caso de que falte algún apellido
    return " ".join(nombre_completo.split())
