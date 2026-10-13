import os
import sys
import getpass
from modulos.auth_guard import generar_hash_contrasena


def main():
    print("=" * 60)
    print("🔐 CONFIGURADOR DE CONTRASEÑA MAESTRA (PBKDF2-SHA256)")
    print("=" * 60)

    if len(sys.argv) > 1:
        clave = sys.argv[1]
    else:
        clave = getpass.getpass("Ingresa tu nueva contraseña maestra: ").strip()
        if not clave:
            print("❌ La contraseña no puede estar vacía.")
            sys.exit(1)
        confirmacion = getpass.getpass("Confirma tu contraseña maestra: ").strip()
        if clave != confirmacion:
            print("❌ Las contraseñas no coinciden.")
            sys.exit(1)

    if len(clave) < 8:
        print("⚠️ Recomendación: Usa al menos 8 caracteres para máxima seguridad.")

    hash_generado = generar_hash_contrasena(clave)

    # Guardar automáticamente en .streamlit/secrets.toml (ignorado por Git)
    os.makedirs(".streamlit", exist_ok=True)
    ruta_secrets = os.path.join(".streamlit", "secrets.toml")

    lineas_existentes = []
    if os.path.exists(ruta_secrets):
        with open(ruta_secrets, "r", encoding="utf-8") as f:
            lineas_existentes = [
                line for line in f.readlines()
                if not line.strip().startswith("APP_PASSWORD_HASH")
            ]

    lineas_existentes.append(f'APP_PASSWORD_HASH = "{hash_generado}"\n')

    with open(ruta_secrets, "w", encoding="utf-8") as f:
        f.writelines(lineas_existentes)

    print("\n✅ Contraseña encriptada y guardada localmente en: .streamlit/secrets.toml")
    print("   (Este archivo está protegido en .gitignore y NO se sube a GitHub).\n")
    print("☁️ Si despliegas en Streamlit Cloud / Render / Servidor en la nube,")
    print("   agrega esta línea en la sección de Secrets / Variables de Entorno:\n")
    print(f'APP_PASSWORD_HASH = "{hash_generado}"')
    print("=" * 60)


if __name__ == "__main__":
    main()
