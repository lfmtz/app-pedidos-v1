import pdfrw
from io import BytesIO
import os


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
