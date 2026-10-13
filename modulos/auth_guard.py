import os
import time
import hmac
import hashlib
import secrets
import streamlit as st

# Configuración de seguridad
ITERACIONES_PBKDF2 = 200_000
MAX_INTENTOS_FALLIDOS = 5
TIEMPO_BLOQUEO_SEGUNDOS = 15 * 60      # 15 minutos de bloqueo tras agotar intentos
TIEMPO_INACTIVIDAD_SEGUNDOS = 30 * 60  # 30 minutos de sesión activa sin actividad


@st.cache_resource
def _estado_seguridad_servidor():
    """
    Almacena el contador de intentos fallidos a nivel de SERVIDOR (compartido entre
    todas las pestañas, navegadores o sesiones de incógnito).
    Así un atacante no puede reiniciar sus intentos abriendo otra ventana.
    """
    return {
        "intentos_fallidos": 0,
        "bloqueado_hasta": 0.0,
    }


def generar_hash_contrasena(contrasena: str, salt_hex: str | None = None) -> str:
    """
    Genera un hash PBKDF2-HMAC-SHA256 con 200,000 iteraciones y salt aleatorio.
    Formato devuelto: 'pbkdf2_sha256$<iteraciones>$<salt_hex>$<hash_hex>'
    """
    if not salt_hex:
        salt_hex = secrets.token_hex(16)
    salt_bytes = bytes.fromhex(salt_hex)
    dk = hashlib.pbkdf2_hmac(
        "sha256",
        contrasena.encode("utf-8"),
        salt_bytes,
        ITERACIONES_PBKDF2,
    )
    return f"pbkdf2_sha256${ITERACIONES_PBKDF2}${salt_hex}${dk.hex()}"


def _verificar_hash(contrasena_ingresada: str, hash_almacenado: str) -> bool:
    """
    Verifica en tiempo constante (hmac.compare_digest) si la contraseña coincide
    con el hash almacenado, evitando ataques de medición de tiempo (timing attacks).
    """
    try:
        partes = hash_almacenado.strip().split("$")
        if len(partes) != 4 or partes[0] != "pbkdf2_sha256":
            return False
        _, iter_str, salt_hex, hash_esperado_hex = partes
        iteraciones = int(iter_str)
        salt_bytes = bytes.fromhex(salt_hex)
        dk = hashlib.pbkdf2_hmac(
            "sha256",
            contrasena_ingresada.encode("utf-8"),
            salt_bytes,
            iteraciones,
        )
        return hmac.compare_digest(dk.hex(), hash_esperado_hex)
    except Exception:
        return False


def _obtener_hash_configurado() -> str | None:
    """
    Busca el hash de la contraseña en variables de entorno o en st.secrets.
    Nunca se almacena la contraseña en texto plano en el código.
    """
    hash_env = os.environ.get("APP_PASSWORD_HASH")
    if hash_env:
        return hash_env.strip()

    try:
        if "APP_PASSWORD_HASH" in st.secrets:
            return str(st.secrets["APP_PASSWORD_HASH"]).strip()
    except Exception:
        pass

    return None


def cerrar_sesion():
    """Limpia por completo el estado de autenticación y datos sensibles en memoria."""
    claves_a_borrar = list(st.session_state.keys())
    for k in claves_a_borrar:
        del st.session_state[k]


def _mostrar_asistente_configuracion_inicial():
    """
    Si APP_PASSWORD_HASH aún no existe, bloquea el sistema y muestra un generador
    de hash para configurar la contraseña maestra fácilmente sin exponerla en el código.
    """
    col_izq, col_centro, col_der = st.columns([1, 1.8, 1])
    with col_centro:
        st.error("🔒 **Sistema Bloqueado: Falta configurar tu contraseña maestra.**")
        st.markdown(
            "El acceso a los datos está **100% detenido**. Crea tu contraseña aquí abajo para generar "
            "tu llave encriptada (`PBKDF2-SHA256`):"
        )

        with st.form("form_generar_hash"):
            nueva_clave = st.text_input("Escribe la contraseña que deseas usar:", type="password")
            confirmar_clave = st.text_input("Confirma tu contraseña:", type="password")
            generar_btn = st.form_submit_button("🔑 Generar Llave Encriptada", use_container_width=True)

        if generar_btn:
            if not nueva_clave:
                st.warning("Escribe una contraseña.")
            elif nueva_clave != confirmar_clave:
                st.error("❌ Las contraseñas no coinciden.")
            elif len(nueva_clave) < 8:
                st.warning("⚠️ Usa al menos 8 caracteres para mayor seguridad.")
            else:
                hash_nuevo = generar_hash_contrasena(nueva_clave)
                st.success("✅ ¡Llave encriptada generada con éxito!")
                st.markdown("**Si estás en Streamlit Cloud / Servidor Web:** copia esta línea y pégala en tus *Secrets* o *Variables de Entorno*:")
                st.code(f'APP_PASSWORD_HASH = "{hash_nuevo}"', language="toml")

                # Si estamos en entorno local (existe credenciales.json), guardar en .streamlit/secrets.toml
                if os.path.exists("credenciales.json"):
                    try:
                        os.makedirs(".streamlit", exist_ok=True)
                        ruta_secrets = os.path.join(".streamlit", "secrets.toml")
                        lineas = []
                        if os.path.exists(ruta_secrets):
                            with open(ruta_secrets, "r", encoding="utf-8") as f:
                                lineas = [
                                    l for l in f.readlines()
                                    if not l.strip().startswith("APP_PASSWORD_HASH")
                                ]
                        lineas.append(f'APP_PASSWORD_HASH = "{hash_nuevo}"\n')
                        with open(ruta_secrets, "w", encoding="utf-8") as f:
                            f.writelines(lineas)
                        st.info("💾 También se guardó automáticamente en `.streamlit/secrets.toml` en tu equipo local. Recarga la página (`F5`) para iniciar sesión.")
                    except Exception:
                        pass


def verificar_acceso():
    """
    Barrera principal de seguridad.
    Si el usuario no está autenticado o su sesión expiró, muestra la pantalla de bloqueo
    y detiene la ejecución del resto de la aplicación con st.stop().
    """
    hash_configurado = _obtener_hash_configurado()

    # 1. Si aún no se ha configurado ningún hash en el servidor/entorno, bloquear el acceso
    if not hash_configurado:
        _mostrar_asistente_configuracion_inicial()
        st.stop()

    ahora = time.time()

    # 2. Verificar si ya tiene sesión iniciada y si no ha expirado por inactividad
    if st.session_state.get("autenticado") is True:
        ultima_actividad = st.session_state.get("ultima_actividad", 0.0)
        if (ahora - ultima_actividad) > TIEMPO_INACTIVIDAD_SEGUNDOS:
            cerrar_sesion()
            st.warning("⏱️ Tu sesión se cerró automáticamente por inactividad. Vuelve a iniciar sesión.")
        else:
            # Renovar marca de tiempo de actividad
            st.session_state["ultima_actividad"] = ahora
            # Mostrar barra lateral con botón de cierre seguro
            with st.sidebar:
                st.markdown("### 🛡️ Sesión Segura Activa")
                st.caption("Acceso exclusivo autorizado.")
                if st.button("🔒 Cerrar Sesión", use_container_width=True):
                    cerrar_sesion()
                    st.rerun()
            return

    # 3. Pantalla de Login protegida contra fuerza bruta
    estado_srv = _estado_seguridad_servidor()

    col_izq, col_centro, col_der = st.columns([1, 1.5, 1])
    with col_centro:
        st.markdown("## 🔐 Acceso Restringido")
        st.caption("Sistema de Gestión de Créditos y Pedidos — Uso exclusivo autorizado.")

        # Verificar si el servidor está en periodo de bloqueo por fuerza bruta
        if ahora < estado_srv["bloqueado_hasta"]:
            segundos_restantes = int(estado_srv["bloqueado_hasta"] - ahora)
            minutos = (segundos_restantes // 60) + 1
            st.error(
                f"🚫 **Acceso bloqueado temporalmente por seguridad.**\n\n"
                f"Se detectaron demasiados intentos fallidos. "
                f"Intenta nuevamente en aproximadamente **{minutos} minuto(s)**."
            )
            st.stop()

        with st.form("form_login_seguro", clear_on_submit=True):
            clave_ingresada = st.text_input(
                "Contraseña maestra:",
                type="password",
                placeholder="Ingresa tu contraseña de acceso",
            )
            submit = st.form_submit_button("Ingresar al Sistema", use_container_width=True)

        if submit:
            if not clave_ingresada:
                st.warning("Ingresa tu contraseña.")
            elif _verificar_hash(clave_ingresada, hash_configurado):
                # Éxito: reiniciar contador de fallos y abrir sesión
                estado_srv["intentos_fallidos"] = 0
                estado_srv["bloqueado_hasta"] = 0.0
                st.session_state["autenticado"] = True
                st.session_state["ultima_actividad"] = time.time()
                st.rerun()
            else:
                # Fallo: pausa anti-bot y registro en memoria del servidor
                time.sleep(1.0)
                estado_srv["intentos_fallidos"] += 1
                intentos_restantes = MAX_INTENTOS_FALLIDOS - estado_srv["intentos_fallidos"]

                if intentos_restantes <= 0:
                    estado_srv["bloqueado_hasta"] = time.time() + TIEMPO_BLOQUEO_SEGUNDOS
                    estado_srv["intentos_fallidos"] = 0
                    st.error(
                        "🚫 **Se agotaron los intentos permitidos.** "
                        "El sistema ha sido bloqueado por 15 minutos."
                    )
                else:
                    st.error(
                        f"❌ Contraseña incorrecta. "
                        f"Intentos restantes antes del bloqueo: **{intentos_restantes}**"
                    )

    # Detener la ejecución para que nada debajo de verificar_acceso() se cargue ni ejecute
    st.stop()
