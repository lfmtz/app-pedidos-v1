import pdfrw
from io import BytesIO
import os
from pdfrw.objects.pdfstring import PdfString
from modulos.procesador_nombres import (
    concatenar_nombre_cliente,
    normalizar_persona_nissan,
)


def _desglosar_fecha_dmy(fecha_raw) -> tuple[str, str, str]:
    """Extrae (dia, mes, anio) desde cadenas DD/MM/YYYY o YYYY-MM-DD."""
    s = str(fecha_raw or "").strip()
    if "/" in s:
        p = s.split("/")
        if len(p) == 3:
            if len(p[0]) == 4:
                return p[2].zfill(2), p[1].zfill(2), p[0]
            return p[0].zfill(2), p[1].zfill(2), p[2]
    elif "-" in s:
        p = s.split("-")
        if len(p) == 3:
            if len(p[0]) == 4:
                return p[2].zfill(2), p[1].zfill(2), p[0]
            return p[0].zfill(2), p[1].zfill(2), p[2]
    return "", "", ""


def generar_solicitud_pdf(datos_cliente):
    import fitz
    import datetime

    # c es el diccionario con los datos del cliente traídos de Google Sheets (SOL_CREDITO_ACTUAL_2026)
    c = datos_cliente

    # --- 1. LÓGICA DE EXTRACCIÓN DE FECHA NACIMIENTO ---
    dia, mes, anio = _desglosar_fecha_dmy(c.get('Fecha de Nacimiento', ''))

    # --- 2. LÓGICA DE SITUACIÓN LABORAL Y MONTOS (COMPATIBLE CON GOOGLE FORM Y APP) ---
    sit_lab_raw = str(c.get('¿Tu situación laboral es actualmente?', '')).strip().upper()
    monto_fijo = str(c.get('Ingreso Fijo', '') or '').strip()
    monto_variable = str(c.get('Ingreso Variable', '') or '').strip()
    monto_cheques = str(c.get('Ingreso Cheques', '') or '').strip()
    monto_neto = str(c.get('Ingresos netos mensuales', '') or '').strip()

    def _es_monto_valido(m: str) -> bool:
        return bool(m) and m not in ('0', '0.0', '0.00', 'NONE', 'NULL')

    val_salario_fijo = ""
    val_salario_variable = ""
    val_cheques_ahorro = ""

    if "ASALARIADO" in sit_lab_raw or "PENSIONADO" in sit_lab_raw or "JUBILADO" in sit_lab_raw:
        val_salario_fijo = monto_fijo if _es_monto_valido(monto_fijo) else (monto_neto if _es_monto_valido(monto_neto) else "")
        if _es_monto_valido(monto_variable):
            val_salario_variable = monto_variable
    elif "INDEPENDIENTE" in sit_lab_raw:
        if _es_monto_valido(monto_cheques):
            val_cheques_ahorro = monto_cheques
        elif _es_monto_valido(monto_neto):
            val_cheques_ahorro = monto_neto
        elif _es_monto_valido(monto_variable):
            val_cheques_ahorro = monto_variable
        elif _es_monto_valido(monto_fijo):
            val_cheques_ahorro = monto_fijo
    else:
        # Si no se especificó situación laboral en el registro, respetar la columna que tenga monto
        if _es_monto_valido(monto_fijo):
            val_salario_fijo = monto_fijo
        if _es_monto_valido(monto_variable):
            val_salario_variable = monto_variable
        if _es_monto_valido(monto_cheques):
            val_cheques_ahorro = monto_cheques
        elif not val_salario_fijo and _es_monto_valido(monto_neto):
            val_salario_fijo = monto_neto

    # --- 3. LÓGICA FECHA DE INGRESO LABORAL ---
    dia_ing, mes_ing, anio_ing = _desglosar_fecha_dmy(
        c.get('Fecha de ingreso a la empresa ó institución', '')
    )

    # --- 4. NORMALIZACIÓN DE NOMBRES (ACREDITADO, CÓNYUGE, REFERENCIAS 1, 2 Y 3) ---
    acre_nom1, acre_nom2, acre_pat, acre_mat = normalizar_persona_nissan(
        c.get('Nombre(s) acreditado', ''),
        c.get('Apellido Paterno acreditado', c.get('Primer apellido acreditado', '')),
        c.get('Apellido Materno acreditado', c.get('Segundo apellido acreditado', '')),
    )

    cy_nom_raw = c.get('Nombre(s) conyuge') or c.get('Nombre(s)_conyuge') or ''
    cy_pat_raw = c.get('Apellido Paterno conyuge') or c.get('Apellido_Paterno_conyuge') or ''
    cy_mat_raw = c.get('Apellido Materno conyuge') or c.get('Apellido_Materno_conyuge') or ''
    cy_nom1, cy_nom2, cy_pat, cy_mat = normalizar_persona_nissan(cy_nom_raw, cy_pat_raw, cy_mat_raw)

    r1_nom1, r1_nom2, r1_pat, r1_mat = normalizar_persona_nissan(
        c.get('Nombre (solo nombre) referencia 1', ''),
        c.get('Apellido Paterno (solo nombre) referencia 1', ''),
        c.get('Apellido Materno (solo nombre) referencia 1', ''),
    )
    r2_nom1, r2_nom2, r2_pat, r2_mat = normalizar_persona_nissan(
        c.get('Nombre (solo nombre) referencia 2', ''),
        c.get('Apellido Paterno (solo nombre) referencia 2', ''),
        c.get('Apellido Materno (solo nombre) referencia 2', ''),
    )
    r3_nom1, r3_nom2, r3_pat, r3_mat = normalizar_persona_nissan(
        c.get('Nombre (solo nombre) referencia 3', ''),
        c.get('Apellido Paterno (solo nombre) referencia 3', ''),
        c.get('Apellido Materno (solo nombre) referencia 3', ''),
    )

    hoy = datetime.date.today()
    nombre_completo_firma = " ".join(p for p in (acre_nom1, acre_nom2, acre_pat, acre_mat) if p)

    # --- 5. DICCIONARIO DE MAPEO EXACTO A LA PLANTILLA DE NISSAN ---
    data_dict = {
        # Fecha de solicitud (encabezado Pág 1 y Pág 2)
        'día': f"{hoy.day:02d}",
        'mes': f"{hoy.month:02d}",
        'año': f"{hoy.year}",
        # Datos personales acreditado
        'Primer Nombre': acre_nom1,
        'Segundo Nombre': acre_nom2,
        'Apellido Paterno': acre_pat,
        'Apellido Materno': acre_mat,
        'RFC con Homoclave': c.get('RFC', ''),
        'CURP': c.get('CURP', ''),
        'País de nacimiento': c.get('País de Nacimiento', ''),
        'Estado de nacimiento': c.get('Entidad Federativa de nacimiento', ''),
        'Número de Celular': c.get('Número Celular', ''),
        'correo electronico': c.get('Correo Electrónico', ''),
        'No de Identificación': c.get('No de Identificación', ''),
        'Autoridad que lo expide': c.get('Autoridad que lo expide identificacion', ''),
        'dia nacimiento': dia,
        'mes naciminiento': mes,  # Mantenemos error ortográfico del PDF original
        'año nacimiento': anio,
        # Cónyuge
        'Primer Nombre_CY': cy_nom1,
        'Segundo Nombre_CY': cy_nom2,
        'Apellido Paterno_CY': cy_pat,
        'Apellido Materno_CY': cy_mat,
        # Domicilio particular
        'Domicilio Particular Calle Av o Vía': c.get('Calle (solo nombre)', ''),
        'No Exterior': c.get('Numero exterior', ''),
        'No Interior': c.get('Numero interior', ''),
        'Colonia o Urbanización': c.get('Colonia acreditado', ''),
        'País de Residencia': c.get('País de Nacimiento', 'MEXICO') if c.get('Calle (solo nombre)') else '',
        'CP': c.get('Código Postal', ''),
        'DelegaciónMunicipio': c.get('Municipio ó Alcaldía', ''),
        'Estado_acre': c.get('Estado', ''),
        'CiudadPoblación Estado_acre': c.get('Ciudad o Población', '') or c.get('Estado', ''),
        'Entre calles del domicilio': c.get('¿Entre que calles esta su domicilio?', ''),
        'Número de Teléfono_CASA': c.get('Teléfono de casa fijo o celular', ''),
        'Años': c.get('Años de vivir en su domicilio', ''),
        # Empleo e ingresos
        'salario_fijo_nom': val_salario_fijo,
        'salario_variable': val_salario_variable,
        'Cheques o Ahorro_salario': val_cheques_ahorro,
        'Nombre de la Empresa': c.get('Nombre de la Empresa ó Institución', ''),
        'Actividad Específica': c.get('¿A que se dedica la empresa donde laboras?', ''),
        'Descipción del empleo o actividad física que desempeña': (
            c.get('¿Qué puesto o actividad desempeñas en tu trabajo?', '')
            or c.get('¿A que se dedica la empresa donde laboras?', '')
        ),
        'Domicilio_trabajo_calle': c.get('Calle trabajo (solo el nombre)', ''),
        'No Exterior_trabajo': c.get('Numero exterior trabajo', ''),
        'No Interior_trabajo': c.get('Numero interior trabajo', ''),
        'Colonia o Urbanización_trabajo': c.get('Colonia trabajo', ''),
        'DelegaciónMunicipio_trabajo': c.get('Municipio ó Alcaldía trabajo', ''),
        'Estado_trabajo': c.get('Estado trabajo', ''),
        'CP_trabajo': c.get('Código Postal trabajo', ''),
        'Telefono_trabajo': c.get('Teléfono de oficina y extensión ó directo', ''),
        'Teléfono de la Empresa': c.get('Teléfono de oficina y extensión ó directo', ''),
        'Nombre del jefe inmediato': c.get('Nombre de tu Jefe Inmediato', ''),
        'Puesto del jefe inmediato': c.get('¿Puesto de jefe inmediato?', ''),
        'dia_ing_tra': dia_ing,
        'mes_ing_tra': mes_ing,
        'año_ing_tra': anio_ing,
        # Referencia 1
        'Primer_Nom_ref_1': r1_nom1,
        'Segundo_Nom_ref_1': r1_nom2,
        'Apellido_Pat_ref_1': r1_pat,
        'Apellido_Mat_ref_1': r1_mat,
        'Parentesco_ref_1': c.get('Parentesco ref 1', ''),
        'Teléfono_cel_ref_1': c.get('Teléfono de la Referencia 1', ''),
        # Referencia 2
        'Primer_Nom_ref_2': r2_nom1,
        'Segundo_Nom_ref_2': r2_nom2,
        'Apellido_Pat_ref_2': r2_pat,
        'Apellido_Mat_ref_2': r2_mat,
        'Parentesco_ref_2': c.get('Parentesco ref 2', ''),
        'Teléfono_cel_ref_2': c.get('Teléfono de la Referencia 2', ''),
        # Referencia 3
        'Primer_Nom_ref_3': r3_nom1,
        'Segundo_Nom_ref_3': r3_nom2,
        'Apellido_Pat_ref_3': r3_pat,
        'Apellido_Mat_ref_3': r3_mat,
        'Parentesco_ref_3': c.get('Parentesco ref 3', ''),
        'Teléfono_cel_ref_3': c.get('Teléfono de la Referencia 3', ''),
        # Firma Página 2
        'Nombre y Firma del Acreditado': nombre_completo_firma,
    }

    # --- 6. PROCESO DE LLENADO CON PYMUPDF (FITZ) SIN SUFIJOS FANTASMA ---
    ruta_plantilla = os.path.join("plantillas", "CN-Solicitud Persona Fisica.pdf")
    if not os.path.exists(ruta_plantilla):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        ruta_plantilla = os.path.join(base_dir, "plantillas", "CN-Solicitud Persona Fisica.pdf")

    if not os.path.exists(ruta_plantilla):
        raise FileNotFoundError(f"No se encontró la plantilla PDF en {ruta_plantilla}")

    doc = fitz.open(ruta_plantilla)

    for page in doc:
        for w in page.widgets():
            key = (w.field_name or "").replace('(', '').replace(')', '').strip()
            # Solo coincidencia exacta del nombre del campo en la plantilla Nissan
            # para evitar llenar por error 'No Exterior_2', 'CP_2', 'Años_2', 'Nombre de la Empresa_3', 'Años_4'
            if key in data_dict:
                val = data_dict[key]
                val_str = str(val).strip() if val is not None else ""
                if val_str and val_str.upper() not in ("NONE", "NULL"):
                    w.field_value = val_str.upper()
                    w.update()

    pdf_bytes = BytesIO(doc.tobytes(garbage=3, deflate=True))
    pdf_bytes.seek(0)
    doc.close()
    return pdf_bytes


def generar_pdf_aviso_privacidad(datos_cliente):
    import fitz
    from io import BytesIO

    ruta_plantilla = os.path.join("plantillas", "aviso_privacidad_stella.pdf")
    if not os.path.exists(ruta_plantilla):
        raise FileNotFoundError(
            f"No se encontró el PDF en: {os.path.abspath(ruta_plantilla)}")

    nombre_completo = concatenar_nombre_cliente(datos_cliente).upper().strip()

    doc = fitz.open(ruta_plantilla)
    for page in doc:
        for w in page.widgets():
            campo = (w.field_name or "").replace('(', '').replace(')', '')
            if campo == 'Nombre Cliente aviso priva':
                w.field_value = nombre_completo
                w.update()

    output_buffer = BytesIO(doc.tobytes(garbage=3, deflate=True))
    output_buffer.seek(0)
    doc.close()

    nombre_descarga = f"Aviso_Privacidad_{nombre_completo.replace(' ', '_') or 'CLIENTE'}.pdf"
    return output_buffer, nombre_descarga


def generar_pdf_stellantis(datos_cliente):
    import fitz
    import re
    import datetime
    from io import BytesIO

    c = datos_cliente

    # 1. Preparación de variables concatenadas
    nom = str(c.get('Nombre(s) acreditado', '')).strip()
    pat = str(c.get('Apellido Paterno acreditado', c.get('Primer apellido acreditado', ''))).strip()
    mat = str(c.get('Apellido Materno acreditado', c.get('Segundo apellido acreditado', ''))).strip()
    nombre_completo_final = f"{nom} {pat} {mat}".strip().upper()

    calle = str(c.get('Calle (solo nombre)', '')).strip()
    num_ext = str(c.get('Numero exterior', '')).strip()
    num_int = str(c.get('Numero interior', '')).strip()
    direccion_completa = f"{calle} EXT: {num_ext} INT: {num_int}".strip().upper()

    # 2. Lógica de fechas
    fecha_nac = str(c.get('Fecha de Nacimiento', '')).strip()
    dia, mes, anio = "", "", ""
    if "/" in fecha_nac:
        partes = fecha_nac.split("/")
        if len(partes) == 3:
            dia, mes, anio = partes[0], partes[1], partes[2]
    elif "-" in fecha_nac:
        partes = fecha_nac.split("-")
        if len(partes) == 3:
            if len(partes[0]) == 4:  # YYYY-MM-DD
                anio, mes, dia = partes[0], partes[1], partes[2]
            else:  # DD-MM-YYYY
                dia, mes, anio = partes[0], partes[1], partes[2]

    fecha_nac_c = str(c.get('Fecha_de_nacimiento_conyuge') or c.get('Fecha de nacimiento conyuge') or '').strip()
    if "-" in fecha_nac_c and "/" not in fecha_nac_c:
        partes_c = fecha_nac_c.split("-")
        if len(partes_c) == 3:
            if len(partes_c[0]) == 4:  # YYYY-MM-DD
                fecha_nac_c = f"{partes_c[2]}/{partes_c[1]}/{partes_c[0]}"
            else:  # DD-MM-YYYY
                fecha_nac_c = f"{partes_c[0]}/{partes_c[1]}/{partes_c[2]}"

    fecha_hoy = datetime.date.today().strftime("%d/%m/%Y")

    # 3. Diccionario de Mapeo Completo (Acreditado, Cónyuge, Referencias, Firmas)
    mapeo_stella = {
        # Datos del acreditado
        'nom_acre': nom.upper(),
        'ape_pat': pat.upper(),
        'ape_mat': mat.upper(),
        'rfc': str(c.get('RFC', '')).upper(),
        'curp': str(c.get('CURP', '')).upper(),
        'nacionalidad': str(c.get('País de Nacimiento', '')).upper(),
        'estado_nacimiento': str(c.get('Entidad Federativa de nacimiento', '')).upper(),
        'fech_lugar_nac': f"{dia}/{mes}/{anio} - {c.get('Entidad Federativa de nacimiento', '')}".upper(),
        'tel_cel': str(c.get('Número Celular', '')),
        'com_telefonica': str(c.get('Compañia telefonica', '')).upper(),
        'correo_elect': str(c.get('Correo Electrónico', '')).lower(),
        'calle': calle.upper(),
        'num_ext_int': f"EXT: {num_ext} INT: {num_int}".upper(),
        'colonia': str(c.get('Colonia acreditado', '')).upper(),
        'codigo_postal': str(c.get('Código Postal', '')),
        'alcaldia_mun': str(c.get('Municipio ó Alcaldía', '')).upper(),
        'estado': str(c.get('Estado', '')).upper(),
        'ciudad_poblacion': str(c.get('Ciudad o Población', '')).upper(),
        'tel_casa': str(c.get('Teléfono de casa fijo o celular', '')),
        'años_residencia': str(c.get('Años de vivir en su domicilio', '')),
        'meses_residencia': '0',
        'ocupa_profesion': str(c.get('¿Qué puesto o actividad desempeñas en tu trabajo?', '')).upper(),
        'nom-empresa': str(c.get('Nombre de la Empresa ó Institución', '')).upper(),
        'giro_empresa': str(c.get('¿A que se dedica la empresa donde laboras?', '')).upper(),
        'calle_empre': str(c.get('Calle trabajo (solo el nombre)', '')).upper(),
        'num_ext_empre': str(c.get('Numero exterior trabajo', '')).upper(),
        'colonia_empre': str(c.get('Colonia trabajo', '')).upper(),
        'alcaldia_empresa': str(c.get('Municipio ó Alcaldía trabajo', '')).upper(),
        'estado_empre': str(c.get('Estado trabajo', '')).upper(),
        'codigo_post_empre': str(c.get('Código Postal trabajo', '')).upper(),
        'tel_oficina': str(c.get('Teléfono de oficina y extensión ó directo', '')),
        'tel_oficina_0': str(c.get('Teléfono de oficina y extensión ó directo', '')),
        'tel_oficina_1': str(c.get('Teléfono de oficina y extensión ó directo', '')),
        'nom_jefe_inmediato': str(c.get('Nombre de tu Jefe Inmediato', '')).upper(),
        'años_empre': str(c.get('Antigüedad en el empleo, negocio ó jubilado ó pensionado años', '')),
        'sueldo_neto': str(c.get('Ingresos netos mensuales', c.get('Ingreso Fijo', ''))),

        # Datos del cónyuge
        'nom_conyuge': str(c.get('Nombre(s)_conyuge') or c.get('Nombre(s) conyuge') or '').upper(),
        'paterno_conyuge': str(c.get('Apellido_Paterno_conyuge') or c.get('Apellido Paterno conyuge') or '').upper(),
        'materno_conyuge': str(c.get('Apellido_Materno_conyuge') or c.get('Apellido Materno conyuge') or '').upper(),
        'nac_conyuge': fecha_nac_c.upper(),
        'nacional_conyuge': str(c.get('NACIONALIDAD_CONYU') or c.get('NACIONALIDAD') or '').upper(),
        'rfc_conyuge': str(c.get('RFC_CONYUGE') or '').upper(),
        'lug_nac_conyuge': str(c.get('Entidad_Federativa_de_nacimiento_conyuge') or c.get('Entidad Federativa de nacimiento conyuge') or '').upper(),
        'curp_conyuge': str(c.get('CURP_CONYUGE') or '').upper(),
        'ocup_conyuge': str(c.get('OCUPACION_CONYUGE') or '').upper(),
        'nom_emp_conyuge': str(c.get('NOM_EMPRESA_CONYUGE') or '').upper(),
        'giro_emp_conyuge': str(c.get('GIRO_EMP_CONYUGE') or c.get('Giro empresa conyuge') or '').upper(),
        'tel_emp_conyuge': str(c.get('TEL_EMPRESA_CONYUGE') or ''),
        'calle_emp_conyuge': str(c.get('CALL_EMPRESA_CONYUGE') or '').upper(),
        'num_ext_int_emp_conyuge': str(c.get('NUM_EXTINT_EM_CONY') or '').upper(),
        'col_emp_conyuge': str(c.get('COL_EM_CONY') or '').upper(),
        'alcal_emp_conyuge': str(c.get('ALC_MUN_EMP_CONY') or '').upper(),
        'cp_emp_conyuge': str(c.get('CP_EMP_CONYUGE') or ''),
        'ciudad_pob_emp_conyuge': str(c.get('CIUDAD_POB_EMP_CONYUGE') or '').upper(),
        'estado_emp_conyuge': str(c.get('ESTADO_EMP_CONYUGE') or '').upper(),
        'ingresos_conyuge': str(c.get('INGRESOS_CONYUGE') or ''),
        'antiguedad_emp_conyuge': str(c.get('ANTIGUEDAD_EMP_CONYUGE') or ''),

        # Referencias
        'ref1_nombre': str(c.get('Nombre (solo nombre) referencia 1', '')).upper(),
        'ref1_parentesco': str(c.get('Parentesco ref 1', '')).upper(),
        'ref1_telefono': str(c.get('Teléfono de la Referencia 1', '')),
        'ref1_ocupacion': str(c.get('Ocupacion de la referencia 1', '')).upper(),
        'ref2_nombre': str(c.get('Nombre (solo nombre) referencia 2', '')).upper(),
        'ref2_parentesco': str(c.get('Parentesco ref 2', '')).upper(),
        'ref2_telefono': str(c.get('Teléfono de la Referencia 2', '')),
        'ref2_ocupacion': str(c.get('Ocupacion de la referencia 2', '')).upper(),
        'ref3_nombre': str(c.get('Nombre (solo nombre) referencia 3', '')).upper(),
        'ref3_parentesco': str(c.get('Parentesco ref 3', '')).upper(),
        'ref3_telefono': str(c.get('Teléfono de la Referencia 3', '')),
        'ref3_ocupacion': str(c.get('Ocupacion de la referencia 3', '')).upper(),

        # Campos Finales
        'nom_final_sol': nombre_completo_final,
        'final_nombre1': nombre_completo_final,
        'final_rfc': str(c.get('RFC', '')).upper(),
        'calle_final_sol': direccion_completa,
        'final_municipio': str(c.get('Municipio ó Alcaldía', '')).upper(),
        'final_estado': str(c.get('Estado', '')).upper(),
        'final_telefono': str(c.get('Número Celular', '')),
        'final_colonia': str(c.get('Colonia acreditado', '')).upper(),
        'final_codigo_postal': str(c.get('Código Postal', '')),
        'nom_vendedor': "LUIS FERNANDO MARTINEZ TREJO",

        # Páginas 2, 3, 4
        '134': nombre_completo_final,
        '3': fecha_hoy,
    }

    # 4. Proceso de llenado robusto con PyMuPDF
    ruta_plantilla = os.path.join("plantillas", "sol_stella.pdf")
    if not os.path.exists(ruta_plantilla):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        ruta_plantilla = os.path.join(base_dir, "plantillas", "sol_stella.pdf")

    if not os.path.exists(ruta_plantilla):
        raise FileNotFoundError(
            f"No se encontró la plantilla en: {os.path.abspath(ruta_plantilla)}")

    doc = fitz.open(ruta_plantilla)

    for page in doc:
        for w in page.widgets():
            key = w.field_name or ""
            key_clean = key.replace('(', '').replace(')', '')
            base_key = re.sub(r'(_\d+|\#\d+|\[\d+\])$', '', key_clean)

            target_val = None
            if key_clean in mapeo_stella:
                target_val = mapeo_stella[key_clean]
            elif base_key in mapeo_stella:
                target_val = mapeo_stella[base_key]
            else:
                for campo_pdf, val in mapeo_stella.items():
                    if (base_key.endswith('.' + campo_pdf) or 
                        key_clean.endswith('.' + campo_pdf)):
                        target_val = val
                        break

            if target_val is not None:
                val_str = str(target_val).strip()
                if val_str:
                    w.field_value = val_str
                    # update() genera el stream de apariencia gráfica /AP garantizando
                    # visibilidad en Foxit Reader, Acrobat Reader, Chrome, Edge y móviles.
                    w.update()

    pdf_bytes = BytesIO(doc.tobytes(garbage=3, deflate=True))
    pdf_bytes.seek(0)
    doc.close()

    nombre_archivo = f"Solicitud_Stellantis_{str(c.get('RFC', 'S_N')).upper()}.pdf"
    return pdf_bytes, nombre_archivo
