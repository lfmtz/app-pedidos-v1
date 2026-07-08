"""
Script de diagnóstico OCR - prueba el nuevo ocr_processor.py mejorado
Uso: python test_ocr_comparativo.py ruta_a_tu_constancia.pdf
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modulos.ocr_processor import procesar_texto_a_diccionario


def diagnostico(ruta_pdf: str):
    with open(ruta_pdf, "rb") as f:
        contenido = f.read()

    resultado = procesar_texto_a_diccionario(contenido)

    print(f"\n{'='*65}")
    print(f"  RESULTADO OCR MEJORADO: {ruta_pdf.split(os.sep)[-1]}")
    print(f"{'='*65}\n")
    print(f"  {'Campo':<48} | Valor extraído")
    print(f"  {'-'*48}-+-{'-'*30}")

    for campo, valor in resultado.items():
        estado = "OK" if valor and valor.strip() else "XX"
        print(f"  [{estado}] {campo:<46} | {valor or '-- VACIO --'}")

    print(f"\n  Total campos detectados: {sum(1 for v in resultado.values() if v and v.strip())}/{len(resultado)}\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("\nUso: python test_ocr_comparativo.py ruta\\constancia.pdf\n")
        sys.exit(1)
    diagnostico(sys.argv[1])
