"""
nissan_solicitud_extractor.py
Extrae los datos de una Solicitud de Crédito Persona Física de Credi Nissan (PDF)
y los mapea a las columnas exactas de la hoja SOL_CREDITO_ACTUAL_2026 (Stellantis / Nissan),
indicando qué campos hicieron match y cuáles quedan pendientes de completar en la app de edición.
"""
import datetime
import re
import fitz


# Campos que Stellantis pide pero el formato impreso de Nissan no incluye
CAMPOS_FALTANTES_STELLANTIS = [
    ("Compañia telefonica", "Compañía telefónica del celular (Telcel, AT&T, Movistar, etc.)"),
    ("Ocupacion de la referencia 1", "Ocupación / empleo de la Referencia 1"),
    ("Ocupacion de la referencia 2", "Ocupación / empleo de la Referencia 2"),
    ("Ocupacion de la referencia 3", "Ocupación / empleo de la Referencia 3"),
]


def _limpiar(val) -> str:
    if val is None:
        return ""
    s = str(val).strip()
    if s.lower() in ("off", "none", "null"):
        return ""
    return re.sub(r"\s+", " ", s)


def _limpiar_apellido_paterno(val: str) -> str:
    """
    En solicitudes de Nissan a veces se anota '<folio>//<vendedor>//<APELLIDO>'
    en el campo Apellido Paterno. Extraemos solo el apellido real.
    """
    s = _limpiar(val)
    if "//" in s:
        partes = [p.strip() for p in s.split("//") if p.strip()]
        if partes:
            return partes[-1].upper()
    return s.upper()


def _limpiar_telefono(val: str) -> str:
    digitos = re.sub(r"\D", "", _limpiar(val))
    if len(digitos) >= 10:
        return digitos[-10:]
    return digitos


def _limpiar_monto(val: str) -> str:
    s = _limpiar(val).replace("$", "").replace(",", "").strip()
    return s


def extraer_datos_solicitud_nissan(pdf_bytes: bytes) -> dict:
    """
    Lee un PDF de Solicitud de Crédito Persona Física de Credi Nissan
    y devuelve un diccionario con:
      - 'campos_sheets': dict con las llaves exactas de SOL_CREDITO_ACTUAL_2026
      - 'resumen_extraidos': dict legible para mostrar en UI
      - 'faltantes_stellantis': lista de campos a completar en la app de edición
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    widgets_por_nombre = {}
    widgets_lista = []

    for page_idx, page in enumerate(doc):
        for w in page.widgets():
            fname = (w.field_name or "").strip()
            fval = _limpiar(w.field_value)
            rect = [round(x, 1) for x in w.rect]
            widgets_lista.append((page_idx, fname, fval, rect))
            if fval and fname not in widgets_por_nombre:
                widgets_por_nombre[fname] = fval

    doc.close()

    def w_get(*nombres) -> str:
        for n in nombres:
            val = widgets_por_nombre.get(n, "")
            if val:
                return val
        return ""

    # ── 1. DATOS PERSONALES DEL ACREDITADO ───────────────────────────────────
    primer_nombre = w_get("Primer Nombre").upper()
    segundo_nombre = w_get("Segundo Nombre").upper()
    nombres_acreditado = f"{primer_nombre} {segundo_nombre}".strip()

    ap_paterno = _limpiar_apellido_paterno(w_get("Apellido Paterno"))
    ap_materno = w_get("Apellido Materno").upper()

    rfc = w_get("RFC con Homoclave", "RFC").upper().replace(" ", "")
    curp = w_get("CURP").upper().replace(" ", "")

    dia_nac = w_get("dia nacimiento").zfill(2) if w_get("dia nacimiento") else ""
    mes_nac = w_get("mes naciminiento", "mes nacimiento").zfill(2) if w_get("mes naciminiento", "mes nacimiento") else ""
    anio_nac = w_get("año nacimiento", "anio nacimiento")
    fecha_nac = f"{dia_nac}/{mes_nac}/{anio_nac}" if (dia_nac and mes_nac and anio_nac) else ""

    pais_nac = w_get("País de nacimiento", "Pais de nacimiento").upper() or "MEXICO"
    estado_nac = w_get("Estado de nacimiento").upper()

    nacion_raw = w_get("nacion", "Nacionalidad").upper()
    nacionalidad = "MEXICANA" if "MEX" in nacion_raw or pais_nac == "MEXICO" else nacion_raw

    sexo_raw = w_get("sexo", "Sexo").upper()
    sexo = "MASCULINO" if sexo_raw == "M" else ("FEMENINO" if sexo_raw == "F" else sexo_raw)

    celular = _limpiar_telefono(w_get("Número de Celular", "Numero de Celular"))

    # En la plantilla V30012024 de Credi Nissan, el campo sobre "Correo electrónico" se llama "Fecha" o "correo electronico"
    correo = w_get("correo electronico", "Correo electrónico")
    if not correo:
        cand_fecha = w_get("Fecha")
        if "@" in cand_fecha:
            correo = cand_fecha
    correo = correo.upper()

    estado_civil_raw = w_get("Estado Civil").upper()
    regimen_mat_raw = w_get("Régimen").upper()
    estado_civil = f"{estado_civil_raw} ({regimen_mat_raw})" if (estado_civil_raw and regimen_mat_raw) else estado_civil_raw

    num_id = w_get("No de Identificación", "No. de Identificación").upper()
    autoridad_id = w_get("Autoridad que lo expide").upper()

    # ── 2. CÓNYUGE ───────────────────────────────────────────────────────────
    nom1_cy = w_get("Primer Nombre_2", "Primer Nombre_CY").upper()
    nom2_cy = w_get("Segundo Nombre_2", "Segundo Nombre_CY").upper()
    nombres_conyuge = f"{nom1_cy} {nom2_cy}".strip()
    ap_pat_conyuge = w_get("Apellido Paterno_2", "Apellido Paterno_CY").upper()
    ap_mat_conyuge = w_get("Apellido Materno_2", "Apellido Materno_CY").upper()

    # ── 3. DOMICILIO PARTICULAR ──────────────────────────────────────────────
    calle = w_get("Domicilio Particular Calle Av o Vía").upper()
    num_ext = w_get("No Exterior").upper()
    num_int = w_get("No Interior").upper()
    colonia = w_get("Colonia o Urbanización").upper()
    entre_calles = w_get("Entre calles del domicilio").upper()
    municipio = w_get("DelegaciónMunicipio").upper()
    ciudad = w_get("CiudadPoblación Estado", "CiudadPoblación Estado_acre").upper()
    estado_dom = w_get("Estado1", "Estado_acre").upper() or ciudad
    cp = re.sub(r"\D", "", w_get("CP"))
    anios_res = w_get("Años")
    tel_casa = _limpiar_telefono(w_get("Número de Teléfono", "Número de Teléfono_CASA")) or celular

    viv_raw = w_get("domicilio").upper()
    tipo_residencia = "FAMILIAR / PADRES" if "PADRE" in viv_raw else viv_raw

    # ── 4. EMPLEO E INGRESOS ─────────────────────────────────────────────────
    ocup_tipo_raw = w_get("acreditado").upper()
    situacion_laboral = "Independiente" if "INDEP" in ocup_tipo_raw else ("Asalariado" if "PRIV" in ocup_tipo_raw or "PUB" in ocup_tipo_raw else ocup_tipo_raw)

    ingreso_fijo = _limpiar_monto(w_get("Fijo", "salario_fijo_nom"))
    ingreso_variable = _limpiar_monto(w_get("Variable"))
    ingreso_cheques = _limpiar_monto(w_get("Cheques o Ahorro", "Cheques o Ahorro_salario"))
    ingreso_neto = ingreso_fijo or ingreso_cheques or ingreso_variable

    nombre_empresa = w_get("Nombre de la Empresa").upper()
    puesto_empleo = w_get("Descipción del empleo o actividad física que desempeña").upper()
    giro_empresa = w_get("Actividad Específica").upper() or puesto_empleo
    tipo_empresa = w_get("tipo Empresa").upper()

    dia_ing = w_get("Text112", "dia_ing_tra").zfill(2) if w_get("Text112", "dia_ing_tra") else ""
    mes_ing = w_get("Text113", "mes_ing_tra").zfill(2) if w_get("Text113", "mes_ing_tra") else ""
    anio_ing = w_get("Text114", "año_ing_tra")
    fecha_ingreso = f"{dia_ing}/{mes_ing}/{anio_ing}" if (dia_ing and mes_ing and anio_ing) else ""

    antiguedad_anios = w_get("Antigüedad en el empleo", "Años_3")
    if not antiguedad_anios and anio_ing and anio_ing.isdigit():
        anio_actual = datetime.date.today().year
        antiguedad_anios = str(max(0, anio_actual - int(anio_ing)))

    calle_trab = w_get("Domicilio Particular Calle Av o Vía_2", "Domicilio_trabajo_calle").upper()
    num_ext_trab = w_get("No Exterior_3", "No Exterior_trabajo").upper()
    num_int_trab = w_get("No Interior_3", "No Interior_trabajo").upper()
    colonia_trab = w_get("Colonia o Urbanización_3", "Colonia o Urbanización_trabajo").upper()
    mun_trab = w_get("DelegaciónMunicipio_2", "DelegaciónMunicipio_trabajo").upper()
    edo_trab = w_get("Estado_2", "Estado_trabajo").upper()
    cp_trab = re.sub(r"\D", "", w_get("CP_3", "CP_trabajo"))
    tel_trab = _limpiar_telefono(w_get("Teléfono de la Empresa", "Telefono_trabajo"))
    jefe_nombre = w_get("Nombre del jefe inmediato").upper() or ("NO APLICA" if "INDEP" in ocup_tipo_raw else "")
    jefe_puesto = w_get("Puesto del jefe inmediato").upper() or ("NO APLICA" if "INDEP" in ocup_tipo_raw else "")

    # ── 5. REFERENCIAS PERSONALES (1, 2 Y 3) ─────────────────────────────────
    # Ref 1
    r1_nom = f"{w_get('Primer Nombre_3', 'Primer_Nom_ref_1')} {w_get('Segundo Nombre_3')}".strip().upper()
    r1_pat = w_get("Apellido Paterno 1", "Apellido_Pat_ref_1").upper()
    r1_mat = w_get("Apellido Materno_3", "Apellido_Mat_ref_1").upper()
    r1_completo = " ".join(p for p in (r1_nom, r1_pat, r1_mat) if p)
    r1_par = w_get("Parentesco", "Parentesco_ref_1").upper()
    r1_tel = _limpiar_telefono(w_get("Teléfono Celular", "Teléfono_cel_ref_1", "Teléfono Domicilio Fijo"))

    # Ref 2
    r2_nom = f"{w_get('Primer Nombre_4', 'Primer_Nom_ref_2')} {w_get('Segundo Nombre_4')}".strip().upper()
    r2_pat = w_get("Apellido Paterno 2", "Apellido_Pat_ref_2").upper()
    r2_mat = w_get("Apellido Materno_4", "Apellido_Mat_ref_2").upper()
    r2_completo = " ".join(p for p in (r2_nom, r2_pat, r2_mat) if p)
    r2_par = w_get("Parentesco_2", "Parentesco_ref_2").upper()
    r2_tel = _limpiar_telefono(w_get("Teléfono Celular_2", "Teléfono_cel_ref_2", "Teléfono Domicilio Fijo_2"))

    # Ref 3
    r3_nom = f"{w_get('Primer Nombre_5', 'Primer_Nom_ref_3')} {w_get('Segundo Nombre_5')}".strip().upper()
    r3_pat = w_get("Apellido Paterno 3", "Apellido_Pat_ref_3").upper()
    r3_mat = w_get("Apellido Materno_5", "Apellido_Mat_ref_3").upper()
    r3_completo = " ".join(p for p in (r3_nom, r3_pat, r3_mat) if p)
    r3_par = w_get("Parentesco_3", "Parentesco_ref_3").upper()
    r3_tel = _limpiar_telefono(w_get("Teléfono Celular_3", "Teléfono_cel_ref_3", "Teléfono Domicilio Fijo_3"))

    ahora_str = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    # Diccionario con las columnas exactas de SOL_CREDITO_ACTUAL_2026
    campos_sheets = {
        "Marca temporal": ahora_str,
        "Timestamp": ahora_str,
        "Nombre(s) acreditado": nombres_acreditado,
        "Apellido Paterno acreditado": ap_paterno,
        "Apellido Materno acreditado": ap_materno,
        "Fecha de Nacimiento": fecha_nac,
        "País de Nacimiento": pais_nac,
        "Entidad Federativa de nacimiento": estado_nac,
        "RFC": rfc,
        "CURP": curp,
        "Sexo": sexo,
        "Nacionalidad": nacionalidad,
        "Número Celular": celular,
        "Correo Electrónico": correo,
        "Casado": estado_civil,
        "Nombre(s) conyuge": nombres_conyuge,
        "Apellido Paterno conyuge": ap_pat_conyuge,
        "Apellido Materno conyuge": ap_mat_conyuge,
        "Nombre(s)_conyuge": nombres_conyuge,
        "Apellido_Paterno_conyuge": ap_pat_conyuge,
        "Apellido_Materno_conyuge": ap_mat_conyuge,
        "¿La identificación que nos proporciona es alguna de las siguientes?": "INE / CREDENCIAL PARA VOTAR" if autoridad_id == "INE" else autoridad_id,
        "No de Identificación": num_id,
        "Autoridad que lo expide identificacion": autoridad_id,
        "Calle (solo nombre)": calle,
        "Numero exterior": num_ext,
        "Numero interior": num_int,
        "Colonia acreditado": colonia,
        "¿Entre que calles esta su domicilio?": entre_calles,
        "Municipio ó Alcaldía": municipio,
        "Estado": estado_dom,
        "Ciudad o Población": ciudad or estado_dom,
        "Código Postal": cp,
        "Tipo de Residencia": tipo_residencia,
        "Años de vivir en su domicilio": anios_res,
        "Teléfono de casa fijo o celular": tel_casa,
        "¿Tu situación laboral es actualmente?": situacion_laboral,
        "Ingreso Fijo": ingreso_fijo,
        "Ingreso Variable": ingreso_variable,
        "Ingreso Cheques": ingreso_cheques,
        "Ingresos netos mensuales": ingreso_neto,
        "Calle trabajo (solo el nombre)": calle_trab,
        "Numero exterior trabajo": num_ext_trab,
        "Numero interior trabajo": num_int_trab,
        "Colonia trabajo": colonia_trab,
        "Municipio ó Alcaldía trabajo": mun_trab,
        "Estado trabajo": edo_trab,
        "Código Postal trabajo": cp_trab,
        "Teléfono de oficina y extensión ó directo": tel_trab,
        "Nombre de la Empresa ó Institución": nombre_empresa,
        "¿Pública ó privada?": tipo_empresa,
        "¿A que se dedica la empresa donde laboras?": giro_empresa,
        "¿Qué puesto o actividad desempeñas en tu trabajo?": puesto_empleo,
        "Fecha de ingreso a la empresa ó institución": fecha_ingreso,
        "Antigüedad en el empleo, negocio ó jubilado ó pensionado años": antiguedad_anios,
        "Nombre de tu Jefe Inmediato": jefe_nombre,
        "¿Puesto de jefe inmediato?": jefe_puesto,
        "¿Eres propietario de negocio?": "SI" if situacion_laboral == "Independiente" else "NO",
        # En Stellantis, "Nombre (solo nombre) referencia X" almacena el nombre completo para el PDF y la App de Edición
        "Nombre (solo nombre) referencia 1": r1_completo,
        "Apellido Paterno (solo nombre) referencia 1": f"{r1_pat} {r1_mat}".strip(),
        "Apellido Materno (solo nombre) referencia 1": r1_mat,
        "Parentesco ref 1": r1_par,
        "Teléfono de la Referencia 1": r1_tel,
        "Nombre (solo nombre) referencia 2": r2_completo,
        "Apellido Paterno (solo nombre) referencia 2": f"{r2_pat} {r2_mat}".strip(),
        "Apellido Materno (solo nombre) referencia 2": r2_mat,
        "Parentesco ref 2": r2_par,
        "Teléfono de la Referencia 2": r2_tel,
        "Nombre (solo nombre) referencia 3": r3_completo,
        "Apellido Paterno (solo nombre) referencia 3": f"{r3_pat} {r3_mat}".strip(),
        "Apellido Materno (solo nombre) referencia 3": r3_mat,
        "Parentesco ref 3": r3_par,
        "Teléfono de la Referencia 3": r3_tel,
    }

    faltantes = [
        {"columna": col, "descripcion": desc}
        for col, desc in CAMPOS_FALTANTES_STELLANTIS
        if not campos_sheets.get(col)
    ]

    return {
        "campos_sheets": campos_sheets,
        "faltantes_stellantis": faltantes,
        "total_widgets_leidos": len(widgets_por_nombre),
    }
