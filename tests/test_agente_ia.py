"""Pruebas unitarias para el módulo agente_ia.py (con cliente Groq simulado)."""

import sys
from pathlib import Path
from types import SimpleNamespace

RAIZ_PROYECTO = Path(__file__).resolve().parent.parent
if str(RAIZ_PROYECTO) not in sys.path:
    sys.path.insert(0, str(RAIZ_PROYECTO))

import agente_ia  # noqa: E402


def _cliente_falso(respuesta_texto: str, captura: dict | None = None):
    """Construye un cliente Groq falso que devuelve `respuesta_texto`."""

    class _Completions:
        def create(self, **kwargs):
            if captura is not None:
                captura["kwargs"] = kwargs
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content=respuesta_texto))]
            )

    return SimpleNamespace(chat=SimpleNamespace(completions=_Completions()))


def test_consultar_detecta_y_limpia_escalar(monkeypatch):
    """Verifica que [ESCALAR] (incluso en negrita) active escalar y se elimine."""
    monkeypatch.setattr(
        agente_ia,
        "_crear_cliente_groq",
        lambda: _cliente_falso("Revisa tu acceso.\n\n**[ESCALAR]**"),
    )

    texto, escalar = agente_ia.consultar("Tengo bloqueado el MFA")
    assert escalar is True
    assert texto == "Revisa tu acceso."


def test_consultar_sin_escalar_y_con_historial(monkeypatch):
    """Verifica que se incluya el historial previo y no escale sin etiqueta."""
    captura = {}
    monkeypatch.setattr(
        agente_ia,
        "_crear_cliente_groq",
        lambda: _cliente_falso("Usa el portal de autoservicio.", captura),
    )

    historial = [
        {"role": "user", "content": "Hola"},
        {"role": "assistant", "content": "¿En qué puedo ayudarte?"},
    ]
    texto, escalar = agente_ia.consultar("¿Cómo cambio mi clave?", historial=historial)

    assert escalar is False
    assert texto == "Usa el portal de autoservicio."
    mensajes_enviados = captura["kwargs"]["messages"]
    assert mensajes_enviados[1]["content"] == "Hola"
    assert mensajes_enviados[2]["content"] == "¿En qué puedo ayudarte?"
    assert mensajes_enviados[3]["content"] == "¿Cómo cambio mi clave?"


def test_clasificar_ticket_json_valido(monkeypatch):
    """Verifica el parseo de categoría y prioridad desde JSON de Groq."""
    monkeypatch.setattr(
        agente_ia,
        "_crear_cliente_groq",
        lambda: _cliente_falso('{"categoria": "Bloqueo de MFA", "prioridad": "alta"}'),
    )

    categoria, prioridad = agente_ia.clasificar_ticket("Perdí mi token MFA")
    assert categoria == "Bloqueo de MFA"
    assert prioridad == "Alta"


def test_clasificar_ticket_fallback_en_error(monkeypatch):
    """Verifica el fallback seguro si Groq falla o devuelve JSON inválido."""
    monkeypatch.setattr(
        agente_ia,
        "_crear_cliente_groq",
        lambda: _cliente_falso("no es json"),
    )

    categoria, prioridad = agente_ia.clasificar_ticket("Algo falló")
    assert categoria == "Incidente de Seguridad"
    assert prioridad == "Media"


def test_consultar_stream_oculta_escalar(monkeypatch):
    """Verifica que consultar_stream transmita el texto sin mostrar [ESCALAR]."""
    chunks = ["Hola ", "mundo.\n", "**[ESCALAR]**"]

    class _StreamCompletions:
        def create(self, **kwargs):
            return [
                SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=c))])
                for c in chunks
            ]

    monkeypatch.setattr(
        agente_ia,
        "_crear_cliente_groq",
        lambda: SimpleNamespace(chat=SimpleNamespace(completions=_StreamCompletions())),
    )

    resultado = {}
    salida = "".join(agente_ia.consultar_stream("MFA bloqueado", resultado=resultado))
    assert salida.strip() == "Hola mundo."
    assert resultado["escalar"] is True
    assert resultado["texto"] == "Hola mundo."
