def concatenar_nombre_cliente(datos):
    """
    Une nombres y apellidos buscando llaves con o sin dos puntos
    para ser compatible con OCR y Google Sheets.
    """
    # Buscamos nombres (Prueba 'Nombre (s):', 'Nombre (s)', 'Nombre(s) acreditado')
    nombres = datos.get("Nombre (s):", datos.get("Nombre (s)", datos.get("Nombre(s) acreditado", ""))).strip()

    # Buscamos primer apellido
    paterno = datos.get("Primer Apellido:", datos.get("Primer Apellido", datos.get("Apellido Paterno acreditado", ""))).strip()

    # Buscamos segundo apellido
    materno = datos.get("Segundo Apellido:", datos.get("Segundo Apellido", datos.get("Apellido Materno acreditado", ""))).strip()

    nombre_completo = f"{nombres} {paterno} {materno}".upper().strip()

    # Si está vacío, intentar con Denominación/Razón Social (Persona Moral)
    if not nombre_completo:
        nombre_completo = str(datos.get("Denominación/Razón Social:", datos.get("Denominación/Razón Social", datos.get("Nombre Comercial:", "")))).upper().strip()

    # Limpia espacios dobles en caso de que falte algún apellido
    return " ".join(nombre_completo.split())
