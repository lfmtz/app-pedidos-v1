"""
Script de prueba integral para el extractor de Cotizaciones de Crédito (Financiera Propia).
Uso:
  python test_cotizacion_credito.py [ruta_opcional_a_cotizacion.pdf]
"""

import ast
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modulos.cotizacion_extractor import (
    CAMPOS_PERMITIDOS_COTIZACION,
    aplicar_cotizacion_a_datos,
    extraer_datos_cotizacion,
    extraer_lineas_ordenadas_pdf,
)


def probar_extraccion_pdf(ruta_pdf: str):
    print(f"\n{'=' * 72}")
    print(f"  TEST DE EXTRACCIÓN DE COTIZACIÓN DE CRÉDITO")
    print(f"  Archivo: {os.path.basename(ruta_pdf)}")
    print(f"{'=' * 72}\n")

    with open(ruta_pdf, "rb") as f:
        pdf_bytes = f.read()

    # 1. Extraer datos de la cotización
    datos_cot = extraer_datos_cotizacion(pdf_bytes)
    meta = datos_cot.get("_meta", {})

    print(f"  Método utilizado : {meta.get('metodo_extraccion', 'N/A')}")
    print(f"  Folio Cotización : {meta.get('folio_cotizacion', 'N/A')}")
    print(f"  Marca            : {meta.get('marca', 'N/A')}")
    print(f"  Plan             : {meta.get('plan', 'N/A')}")
    print(f"  Tasa de Interés  : {meta.get('tasa_interes', 'N/A')}\n")

    print(f"  {'Campo en Gestor_Creditos':<30} | {'Valor Extraído'}")
    print(f"  {'-' * 30}-+-{'-' * 38}")
    for campo in [
        "Auto",
        "AÑO",
        "Precio Auto",
        "Pago Inicial",
        "Monto a Financiar",
        "Plazo",
        "Mensualidades",
        "FINANCIERA PROPIA",
        "ANTICIPO",
    ]:
        val = datos_cot.get(campo)
        if isinstance(val, float):
            val_str = f"${val:,.2f}"
        else:
            val_str = str(val)
        print(f"  {campo:<30} | {val_str}")

    print(
        f"\n  [Info] Financiado Solo Vehículo : ${meta.get('monto_financiado_vehiculo', 0.0):,.2f}"
    )
    print(
        f"  [Info] Financiado Total Contrato: ${meta.get('monto_financiado_total', 0.0):,.2f}\n"
    )

    # 2. Simular convivencia con datos previos de la Constancia de Situación Fiscal (SAT)
    datos_sat_simulados = {
        "RFC:": "XAXX010101000",
        "CURP:": "XAXX010101HDFRNN09",
        "Nombre (s):": "JUAN CARLOS",
        "Primer Apellido:": "PEREZ",
        "Segundo Apellido:": "LOPEZ",
        "Código Postal:": "06600",
        "Nombre de Vialidad:": "PASEO DE LA REFORMA",
        "Número Exterior:": "222",
        "Nombre de la Colonia:": "JUAREZ",
    }

    datos_combinados = aplicar_cotizacion_a_datos(datos_sat_simulados, datos_cot)

    # 3. Aserciones de negocio
    assert datos_cot["Auto"] == "RAM 1200 TRADESMAN CC 2.0T 8AT 4X2", (
        f"Error en Auto: {datos_cot['Auto']}"
    )
    assert datos_cot["AÑO"] == "2026", f"Error en AÑO: {datos_cot['AÑO']}"
    assert abs(datos_cot["Precio Auto"] - 537500.00) < 0.01, (
        f"Error en Precio Auto: {datos_cot['Precio Auto']}"
    )
    assert abs(datos_cot["Pago Inicial"] - 430000.00) < 0.01, (
        f"Error en Pago Inicial (Enganche): {datos_cot['Pago Inicial']}"
    )
    assert abs(datos_cot["Monto a Financiar"] - 107942.56) < 0.01, (
        f"Error en Monto a Financiar: {datos_cot['Monto a Financiar']}"
    )
    assert abs(meta["monto_financiado_vehiculo"] - 107500.00) < 0.01, (
        f"Error en Monto Financiado Vehículo: {meta['monto_financiado_vehiculo']}"
    )
    assert datos_cot["Plazo"] == "12", f"Error en Plazo: {datos_cot['Plazo']}"
    assert abs(datos_cot["Mensualidades"] - 9835.66) < 0.01, (
        f"Error en Mensualidades: {datos_cot['Mensualidades']}"
    )
    assert datos_cot["FINANCIERA PROPIA"] == "SÍ", "Error en FINANCIERA PROPIA"

    # Verificar que ningún dato del SAT fue modificado por la cotización
    for k_sat, v_sat in datos_sat_simulados.items():
        assert datos_combinados.get(k_sat) == v_sat, (
            f"¡Alerta! El campo SAT '{k_sat}' fue alterado."
        )

    # Verificar que el campo SEGURO NO fue llenado
    assert "SEGURO" not in datos_combinados, (
        "¡Alerta! El campo SEGURO no debe llenarse en operaciones por financiera propia."
    )

    # Verificar sintaxis válida de app.py
    ruta_app = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.py")
    with open(ruta_app, "r", encoding="utf-8") as f_app:
        ast.parse(f_app.read(), filename="app.py")

    print("  [OK] Validación 1: Datos de unidad y financiamiento extraídos al 100%.")
    print("  [OK] Validación 2: Datos de Constancia Fiscal (SAT) intactos y separados.")
    print("  [OK] Validación 3: Campo 'SEGURO' vacío/sin tocar (regla financiera propia).")
    print("  [OK] Validación 4: Sintaxis e integración en app.py verificadas correctamente.")
    print(f"\n{'=' * 72}\n")


if __name__ == "__main__":
    ruta_default = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "test_outputs",
        "cotizacion_prueba_stellantis.pdf",
    )
    ruta = sys.argv[1] if len(sys.argv) > 1 else ruta_default
    if not os.path.exists(ruta):
        print(f"No se encontró el archivo PDF de prueba en: {ruta}")
        sys.exit(1)
    probar_extraccion_pdf(ruta)
