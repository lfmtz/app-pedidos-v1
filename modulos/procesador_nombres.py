def concatenar_nombre_cliente(datos):
    """
    Toma los nombres y apellidos por separado y los une
    específicamente para el Aviso de Privacidad de Stella Motors.
    """
    # Extraemos con .get para evitar errores si el campo viene vacío
    nombres = datos.get("Nombre (s):", "").strip()
    paterno = datos.get("Primer Apellido:", "").strip()
    materno = datos.get("Segundo Apellido:", "").strip()

    # Unimos los componentes
    nombre_completo = f"{nombres} {paterno} {materno}".upper()

    # Devolvemos el nombre limpio (quitando espacios dobles si no hay segundo apellido)
    return " ".join(nombre_completo.split())
