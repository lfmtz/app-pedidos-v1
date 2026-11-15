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


def separar_primer_y_segundo_nombre(nombres_str: str) -> tuple[str, str]:
    """
    Divide una cadena de nombre(s) de pila en (primer_nombre, segundo_nombre)
    para las casillas 'Primer Nombre' y 'Segundo Nombre' del PDF de Nissan.
    Respeta artículos compuestos (ej. 'MARIA DEL CARMEN' -> ('MARIA', 'DEL CARMEN')).
    """
    limpio = " ".join(str(nombres_str or "").strip().upper().split())
    if not limpio:
        return "", ""
    partes = limpio.split(" ")
    if len(partes) == 1:
        return partes[0], ""
    return partes[0], " ".join(partes[1:])


def normalizar_persona_nissan(nombres_raw, ap_pat_raw, ap_mat_raw) -> tuple[str, str, str, str]:
    """
    Normaliza los datos de una persona (Acreditado, Cónyuge o Referencia) exclusivamente
    para la Solicitud PDF de Nissan, devolviendo:
        (primer_nombre, segundo_nombre, apellido_paterno, apellido_materno)

    Soporta tanto:
      1. Registros del Google Form / App Nissan (donde cada columna trae su valor separado:
         Nombre(s), Apellido Paterno, Apellido Materno).
      2. Registros donde en la columna de Nombre se capturó el nombre completo con apellidos
         (ej. Stellantis o capturas mixtas), evitando duplicar apellidos en el PDF de Nissan.
    """
    nom = " ".join(str(nombres_raw or "").strip().upper().split())
    pat = " ".join(str(ap_pat_raw or "").strip().upper().split())
    mat = " ".join(str(ap_mat_raw or "").strip().upper().split())

    # Si ap_pat contiene a ap_mat duplicado al final (ej. pat="PEINADO DELGADO", mat="DELGADO")
    if pat and mat and pat != mat and pat.endswith(" " + mat):
        pat = pat[: -(len(mat) + 1)].strip()

    # Si nom termina con "pat mat" o con "pat" (cuando escribieron el nombre completo en la columna de nombre)
    sufijo_completo = " ".join(p for p in (pat, mat) if p)
    if sufijo_completo and nom.endswith(" " + sufijo_completo):
        nom = nom[: -(len(sufijo_completo) + 1)].strip()
    elif pat and nom.endswith(" " + pat):
        nom = nom[: -(len(pat) + 1)].strip()

    # Caso en que ap_pat y ap_mat están vacíos pero nom tiene nombre completo (>= 3 palabras)
    if nom and not pat and not mat:
        tokens = nom.split(" ")
        if len(tokens) >= 3:
            mat = tokens[-1]
            pat = tokens[-2]
            nom = " ".join(tokens[:-2])
        elif len(tokens) == 2:
            pat = tokens[-1]
            nom = tokens[0]

    # Caso en que ap_mat está vacío y ap_pat tiene los dos apellidos (ej. "GONZALEZ ORTIZ")
    # solo si nom NO está vacío
    primer_nom, segundo_nom = separar_primer_y_segundo_nombre(nom)
    return primer_nom, segundo_nom, pat, mat

