import pdfrw
from io import BytesIO
import os
from pdfrw.objects.pdfstring import PdfString
from modulos.procesador_nombres import concatenar_nombre_cliente


def generar_solicitud_pdf(datos_cliente):
    # c es el diccionario con los datos del cliente traídos de Google Sheets
    c = datos_cliente

    # --- 1. LÓGICA DE EXTRACCIÓN DE FECHA NACIMIENTO ---
    fecha_nac = str(c.get('Fecha de Nacimiento', ''))
    dia, mes, anio = "", "", ""
    if "/" in fecha_nac:
        partes = fecha_nac.split("/")
        if len(partes) == 3:
            dia, mes, anio = partes[0], partes[1], partes[2]

    # --- 2. LÓGICA DE SITUACIÓN LABORAL Y MONTOS ---
    sit_lab = str(c.get('¿Tu situación laboral es actualmente?', '')).strip()
    monto_fijo = str(c.get('Ingreso Fijo', '0'))
    monto_variable = str(c.get('Ingreso Variable', '0'))

    val_salario_fijo = ""
    val_cheques_ahorro = ""

    # Lógica idéntica a tu código original
    if sit_lab in ['Asalariado', 'Pensionado ó Jubilado']:
        val_salario_fijo = monto_fijo
    elif sit_lab == 'Independiente':
        val_cheques_ahorro = monto_variable

    # --- 3. LÓGICA FECHA DE INGRESO LABORAL ---
    fecha_ingreso = str(
        c.get('Fecha de ingreso a la empresa ó institución', ''))
    dia_ing, mes_ing, anio_ing = "", "", ""
    if "/" in fecha_ingreso:
        p_ing = fecha_ingreso.split("/")
        if len(p_ing) == 3:
            dia_ing, mes_ing, anio_ing = p_ing[0], p_ing[1], p_ing[2]

    # --- 4. DICCIONARIO DE MAPEO COMPLETO ---
    data_dict = {
        'Primer Nombre': c.get('Nombre(s) acreditado'),
        'Apellido Paterno': c.get('Apellido Paterno acreditado'),
        'Apellido Materno': c.get('Apellido Materno acreditado'),
        'RFC con Homoclave': c.get('RFC'),
        'CURP': c.get('CURP'),
        'País de nacimiento': c.get('País de Nacimiento'),
        'Estado de nacimiento': c.get('Entidad Federativa de nacimiento'),
        'Número de Celular': str(c.get('Número Celular')),
        'correo electronico': c.get('Correo Electrónico'),
        'No de Identificación': str(c.get('No de Identificación')),
        'Autoridad que lo expide': c.get('Autoridad que lo expide identificacion'),
        'dia nacimiento': dia,
        'mes naciminiento': mes,  # Mantenemos error ortográfico del PDF
        'año nacimiento': anio,
        'Primer Nombre_CY': c.get('Nombre(s) conyuge'),
        'Apellido Paterno_CY': c.get('Apellido Paterno conyuge'),
        'Apellido Materno_CY': c.get('Apellido Materno conyuge'),
        'Domicilio Particular Calle Av o Vía': c.get('Calle (solo nombre)'),
        'No Exterior': str(c.get('Numero exterior')),
        'No Interior': str(c.get('Numero interior')),
        'Colonia o Urbanización': c.get('Colonia acreditado'),
        'CP': str(c.get('Código Postal')),
        'DelegaciónMunicipio': c.get('Municipio ó Alcaldía'),
        'Estado_acre': c.get('Estado'),
        'CiudadPoblación Estado_acre': c.get('Ciudad o Población'),
        'Entre calles del domicilio': c.get('¿Entre que calles esta su domicilio?'),
        'Número de Teléfono_CASA': str(c.get('Teléfono de casa fijo o celular')),
        'Años': str(c.get('Años de vivir en su domicilio')),
        'salario_fijo_nom': val_salario_fijo,
        'Cheques o Ahorro_salario': val_cheques_ahorro,
        'Nombre de la Empresa': c.get('Nombre de la Empresa ó Institución'),
        'Actividad Específica': c.get('¿A que se dedica la empresa donde laboras?'),
        'Descipción del empleo o actividad física que desempeña': c.get('¿Qué puesto o actividad desempeñas en tu trabajo?'),
        'Domicilio_trabajo_calle': c.get('Calle trabajo (solo el nombre)'),
        'No Exterior_trabajo': str(c.get('Numero exterior trabajo')),
        'No Interior_trabajo': str(c.get('Numero interior trabajo')),
        'Colonia o Urbanización_trabajo': c.get('Colonia trabajo'),
        'DelegaciónMunicipio_trabajo': c.get('Municipio ó Alcaldía trabajo'),
        'Estado_trabajo': c.get('Estado trabajo'),
        'CP_trabajo': str(c.get('Código Postal trabajo')),
        'Telefono_trabajo': str(c.get('Teléfono de oficina y extensión ó directo')),
        'Teléfono de la Empresa': str(c.get('Teléfono de oficina y extensión ó directo')),
        'Nombre del jefe inmediato': c.get('Nombre de tu Jefe Inmediato'),
        'Puesto del jefe inmediato': c.get('¿Puesto de jefe inmediato?'),
        'Antigüedad en el empleo': str(c.get('Antigüedad en el empleo, negocio ó jubilado ó pensionado años')),
        'dia_ing_tra': dia_ing,
        'mes_ing_tra': mes_ing,
        'año_ing_tra': anio_ing,
        'Primer_Nom_ref_1': c.get('Nombre (solo nombre) referencia 1'),
        'Apellido_Pat_ref_1': c.get('Apellido Paterno (solo nombre) referencia 1'),
        'Apellido_Mat_ref_1': c.get('Apellido Materno (solo nombre) referencia 1'),
        'Parentesco_ref_1': c.get('Parentesco ref 1'),
        'Teléfono_cel_ref_1': str(c.get('Teléfono de la Referencia 1')),
        'Primer_Nom_ref_2': c.get('Nombre (solo nombre) referencia 2'),
        'Apellido_Pat_ref_2': c.get('Apellido Paterno (solo nombre) referencia 2'),
        'Apellido_Mat_ref_2': c.get('Apellido Materno (solo nombre) referencia 2'),
        'Parentesco_ref_2': c.get('Parentesco ref 2'),
        'Teléfono_cel_ref_2': str(c.get('Teléfono de la Referencia 2')),
        'Primer_Nom_ref_3': c.get('Nombre (solo nombre) referencia 3'),
        'Apellido_Pat_ref_3': c.get('Apellido Paterno (solo nombre) referencia 3'),
        'Apellido_Mat_ref_3': c.get('Apellido Materno (solo nombre) referencia 3'),
        'Parentesco_ref_3': c.get('Parentesco ref 3'),
        'Teléfono_cel_ref_3': str(c.get('Teléfono de la Referencia 3'))
    }

    # --- 5. PROCESO DE LLENADO ---
    ruta_plantilla = os.path.join(
        "plantillas", "CN-Solicitud Persona Fisica.pdf")
    try:
        template = pdfrw.PdfReader(ruta_plantilla)
    except Exception:
        raise Exception("No se encontró la plantilla PDF en {ruta_plantilla}")

    for page in template.pages:
        annotations = page.get('/Annots')
        if annotations:
            for ann in annotations:
                if ann.get('/Subtype') == '/Widget':
                    # Limpiamos el nombre del campo del PDF
                    key = ann.get('/T')
                    if key:
                        key = key.replace('(', '').replace(')', '')
                        if key in data_dict:
                            val = data_dict[key]
                            val_str = str(val) if val is not None else ""
                            # Inyectar valor en MAYÚSCULAS
                            ann.update(pdfrw.PdfDict(
                                V='{}'.format(val_str.upper())))

    # Fuerza visibilidad de datos
    if not template.Root.AcroForm:
        template.Root.AcroForm = pdfrw.PdfDict()
    template.Root.AcroForm.update(pdfrw.PdfDict(
        NeedAppearances=pdfrw.PdfObject('true')))

    # Guardar en memoria para que Streamlit pueda descargarlo
    pdf_bytes = BytesIO()
    pdfrw.PdfWriter().write(pdf_bytes, template)
    pdf_bytes.seek(0)
    return pdf_bytes


def generar_pdf_aviso_privacidad(datos_cliente):
    # 1. RUTA RELATIVA (Funciona en tu PC y en Streamlit Cloud)
    ruta_plantilla = os.path.join("plantillas", "aviso_privacidad_stella.pdf")

    if not os.path.exists(ruta_plantilla):
        raise FileNotFoundError(
            f"No se encontró el PDF en: {os.path.abspath(ruta_plantilla)}")

    # 2. NOMBRE CONCATENADO EN MAYÚSCULAS
    nombre_completo = concatenar_nombre_cliente(datos_cliente).upper()

    # 3. LECTURA DE PLANTILLA
    try:
        template = pdfrw.PdfReader(ruta_plantilla)
    except Exception as e:
        raise Exception(f"Error crítico al leer el PDF: {e}")

    # --- LÓGICA DE VISIBILIDAD FORZADA ---
    # Forzamos que el lector de PDF dibuje los campos al abrir
    if not template.Root.AcroForm:
        template.Root.AcroForm = pdfrw.PdfDict()

    template.Root.AcroForm.update(pdfrw.PdfDict(
        NeedAppearances=pdfrw.PdfObject('true')))

    # 4. LLENADO DEL CAMPO
    for page in template.pages:
        annotations = page.get('/Annots')
        if annotations:
            for annotation in annotations:
                nombre_campo_pdf = annotation.get('/T')
                if nombre_campo_pdf:
                    # Limpiamos paréntesis del nombre técnico del campo para compararlo
                    nombre_campo_pdf = nombre_campo_pdf.replace(
                        '(', '').replace(')', '')

                # BUSCAMOS TU CAMPO ESPECÍFICO
                if nombre_campo_pdf == 'Nombre Cliente aviso priva':
                    # Inyectamos el nombre.
                    # f'({valor})' es el formato interno de PDF, no imprime los paréntesis.
                    from pdfrw.objects.pdfstring import PdfString
                    # annotation.update(pdfrw.PdfDict(V=f'({nombre_completo})'))
                    val_enc = PdfString.encode(nombre_completo)
                    annotation.update(pdfrw.PdfDict(V=val_enc))

                    # ELIMINAMOS LA APARIENCIA PREVIA (/AP)
                    # Esto es lo que quita el "efecto fantasma"
                    if '/AP' in annotation:
                        del annotation['/AP']

    # 5. GENERAR EN MEMORIA (BytesIO)
    output_buffer = BytesIO()
    pdfrw.PdfWriter().write(output_buffer, template)
    output_buffer.seek(0)

    # 6. NOMBRE DEL ARCHIVO PARA DESCARGA
    nombre_descarga = f"Aviso_Privacidad_{nombre_completo.replace(' ', '_')}.pdf"

    return output_buffer, nombre_descarga


def generar_pdf_stellantis(datos_cliente):
    c = datos_cliente
    from pdfrw.objects.pdfstring import PdfString

    # 1. Preparación de variables concatenadas
    nom = str(c.get('Nombre(s) acreditado', '')).strip()
    pat = str(c.get('Apellido Paterno acreditado', '')).strip()
    mat = str(c.get('Apellido Materno acreditado', '')).strip()
    nombre_completo_final = f"{nom} {pat} {mat}".strip().upper()

    calle = str(c.get('Calle (solo nombre)', '')).strip()
    num_ext = str(c.get('Numero exterior', '')).strip()
    num_int = str(c.get('Numero interior', '')).strip()
    direccion_completa = f"{calle} EXT: {num_ext} INT: {num_int}".strip(
    ).upper()

    # 2. Lógica de fechas
    fecha_nac = str(c.get('Fecha de Nacimiento', ''))
    dia, mes, anio = "", "", ""
    if "/" in fecha_nac:
        partes = fecha_nac.split("/")
        if len(partes) == 3:
            dia, mes, anio = partes[0], partes[1], partes[2]

    # 3. Diccionario de Mapeo (Asegúrate de que los nombres coincidan con los del PDF)
    mapeo_stella = {
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
        'nom_jefe_inmediato': str(c.get('Nombre de tu Jefe Inmediato', '')).upper(),
        'años_empre': str(c.get('Antigüedad en el empleo, negocio ó jubilado ó pensionado años', '')),
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
    }

    # 4. Proceso de llenado robusto
    ruta_plantilla = os.path.join("plantillas", "sol_stella.pdf")
    template = pdfrw.PdfReader(ruta_plantilla)

    for page in template.pages:
        annotations = page.get('/Annots')
        if annotations:
            for ann in annotations:
                # IMPORTANTE: Filtrar por /Widget como en Nissan
                if ann.get('/Subtype') == '/Widget':
                    key = ann.get('/T')
                    if key:
                        # Limpiar nombre técnico del campo
                        key = key.replace('(', '').replace(')', '')

                        # Si el PDF usa nombres largos tipo 'f1_05[0].final_nombre[0]'
                        # buscamos si nuestra clave está contenida al final del nombre
                        for campo_pdf in mapeo_stella:
                            if key == campo_pdf or key.endswith('.' + campo_pdf) or key.endswith(campo_pdf):
                                val = mapeo_stella[campo_pdf]
                                val_str = str(val).upper(
                                ) if val is not None else ""

                                # Inyectar con PdfString.encode para evitar paréntesis impresos
                                ann.update(pdfrw.PdfDict(
                                    V=PdfString.encode(val_str)))

                                if '/AP' in ann:
                                    del ann['/AP']
                                break

    # 5. Visibilidad y Generación
    if not template.Root.AcroForm:
        template.Root.AcroForm = pdfrw.PdfDict()
    template.Root.AcroForm.update(pdfrw.PdfDict(
        NeedAppearances=pdfrw.PdfObject('true')))

    pdf_bytes = BytesIO()
    pdfrw.PdfWriter().write(pdf_bytes, template)
    pdf_bytes.seek(0)

    nombre_archivo = f"Solicitud_Stellantis_{str(c.get('RFC', 'S_N')).upper()}.pdf"
    return pdf_bytes, nombre_archivo
