"""Interfaz de chat en Streamlit para el Asistente de Soporte TI y Ciberseguridad."""

import logging
import os
import time
import streamlit as st
from groq import GroqError

from agente_ia import clasificar_ticket, consultar_stream
from automatizacion import generar_ticket

TITULO_APP = "Asistente Automatizado de Soporte TI y Ciberseguridad (Nivel 1)"
MAX_PREGUNTA_CHARS = 2000
COOLDOWN_SEGUNDOS = 3.0
logger = logging.getLogger(__name__)


def inicializar_estado() -> None:
    """Inicializa el estado de la sesión en `st.session_state`."""
    if "mensajes" not in st.session_state:
        st.session_state.mensajes = []
    if "usuario" not in st.session_state:
        st.session_state.usuario = ""
    if "ticket_abierto" not in st.session_state:
        st.session_state.ticket_abierto = False
    if "ultimo_envio" not in st.session_state:
        st.session_state.ultimo_envio = 0.0


def solicitar_nombre_usuario() -> None:
    """Muestra un formulario inicial para capturar el nombre del solicitante."""
    st.info("Bienvenido. Por favor ingresa tu nombre para iniciar la atención.")
    with st.form("form_solicitante"):
        nombre = st.text_input(
            "Nombre completo",
            placeholder="Ej. Ana García",
            max_chars=100,
        )
        enviado = st.form_submit_button("Iniciar chat")

    if enviado:
        nombre_limpio = nombre.strip()
        if not nombre_limpio:
            st.warning("Por favor escribe tu nombre para continuar.")
            return
        st.session_state.usuario = nombre_limpio
        st.rerun()


def mostrar_historial() -> None:
    """Renderiza los mensajes previos almacenados en la sesión."""
    for mensaje in st.session_state.mensajes:
        with st.chat_message(mensaje["role"]):
            st.markdown(mensaje["content"])
            if mensaje.get("ticket"):
                st.success("Ticket generado")


def main() -> None:
    """Punto de entrada principal de la aplicación Streamlit."""
    st.set_page_config(page_title=TITULO_APP, page_icon="🛡️")
    st.title(TITULO_APP)

    inicializar_estado()

    if not os.environ.get("GROQ_API_KEY"):
        st.error(
            "No se encontró la variable de entorno `GROQ_API_KEY`. "
            "Por favor, configúrala antes de enviar consultas al asistente."
        )

    if not st.session_state.usuario:
        solicitar_nombre_usuario()
        return

    with st.sidebar:
        st.header("Información del solicitante")
        st.markdown(f"**Solicitante:** {st.session_state.usuario}")
        if st.button("Limpiar chat", use_container_width=True):
            st.session_state.mensajes = []
            st.session_state.ticket_abierto = False
            st.rerun()
        if st.button("Cambiar solicitante", use_container_width=True):
            st.session_state.usuario = ""
            st.session_state.mensajes = []
            st.session_state.ticket_abierto = False
            st.rerun()

    mostrar_historial()

    pregunta = st.chat_input("Describe tu consulta o incidente de TI / ciberseguridad...")
    if not pregunta:
        return

    ahora = time.monotonic()
    transcurrido = ahora - st.session_state.ultimo_envio
    if st.session_state.ultimo_envio and transcurrido < COOLDOWN_SEGUNDOS:
        restante = max(1, int(COOLDOWN_SEGUNDOS - transcurrido + 0.9))
        st.warning(f"Por favor espera {restante} s antes de enviar otra consulta.")
        return

    if len(pregunta) > MAX_PREGUNTA_CHARS:
        st.warning(
            f"La consulta excede el límite permitido de {MAX_PREGUNTA_CHARS} caracteres. "
            "Por favor, resúmela e inténtalo nuevamente."
        )
        return

    st.session_state.ultimo_envio = ahora
    historial_previo = list(st.session_state.mensajes)
    st.session_state.mensajes.append({"role": "user", "content": pregunta})
    with st.chat_message("user"):
        st.markdown(pregunta)

    with st.chat_message("assistant"):
        resultado: dict[str, object] = {}
        try:
            st.write_stream(
                consultar_stream(pregunta, historial=historial_previo, resultado=resultado)
            )
            respuesta = str(resultado.get("texto", ""))
            escalar = bool(resultado.get("escalar", False))
        except RuntimeError as exc:
            st.error(f"Error de configuración: {exc}")
            return
        except GroqError:
            logger.exception("Error al comunicarse con la API de Groq.")
            st.error(
                "No fue posible comunicarse con el servicio de IA en este momento. "
                "Inténtalo nuevamente en unos instantes."
            )
            return
        except Exception:
            logger.exception("Error inesperado al procesar la consulta.")
            st.error("Ocurrió un error inesperado al procesar tu consulta.")
            return

        ticket_generado = False
        if escalar:
            if not st.session_state.ticket_abierto:
                categoria, prioridad = clasificar_ticket(pregunta)
                generar_ticket(
                    st.session_state.usuario,
                    categoria,
                    pregunta,
                    prioridad=prioridad,
                )
                st.session_state.ticket_abierto = True
                ticket_generado = True
                st.success("Ticket generado")
            else:
                st.info("Tu incidente ya cuenta con un ticket abierto en esta conversación.")

        st.session_state.mensajes.append(
            {
                "role": "assistant",
                "content": respuesta,
                "ticket": ticket_generado,
            }
        )


if __name__ == "__main__":
    main()
