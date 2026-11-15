"""Pruebas unitarias para el módulo automatizacion.py (sin llamadas a Groq)."""

import hashlib
import hmac
import re
import sys
from pathlib import Path
from unittest.mock import MagicMock

from openpyxl import load_workbook

RAIZ_PROYECTO = Path(__file__).resolve().parent.parent
if str(RAIZ_PROYECTO) not in sys.path:
    sys.path.insert(0, str(RAIZ_PROYECTO))

from automatizacion import _notificar_webhook, generar_ticket  # noqa: E402


def test_generar_ticket_crea_y_reutiliza_excel_diario(tmp_path, monkeypatch):
    """Verifica la creación del Excel diario, encabezados e IDs secuenciales."""
    monkeypatch.chdir(tmp_path)

    usuario_1 = "ana.garcia@empresa.com"
    tipo_1 = "Bloqueo de MFA"
    desc_1 = "El token MFA no responde tras cambiar de dispositivo."

    ruta_1 = generar_ticket(usuario_1, tipo_1, desc_1, prioridad="Alta")
    archivo = Path(ruta_1)

    assert archivo.exists()
    assert archivo.parent.name == "tickets"
    assert re.fullmatch(r"tickets_\d{4}-\d{2}-\d{2}\.xlsx", archivo.name)

    ruta_2 = generar_ticket("luis.perez", "Phishing", "Correo sospechoso.", prioridad="Media")
    assert Path(ruta_2) == archivo

    wb = load_workbook(archivo)
    assert "Tickets" in wb.sheetnames
    ws = wb["Tickets"]

    filas = list(ws.iter_rows(values_only=True))
    assert len(filas) == 3
    assert list(filas[0]) == ["ID", "Fecha / Hora", "Usuario", "Categoría", "Prioridad", "Descripción"]
    assert filas[1][0] == "TICK-000001"
    assert filas[1][1]  # fecha/hora no vacía
    assert list(filas[1][2:]) == [usuario_1, tipo_1, "Alta", desc_1]
    assert filas[2][0] == "TICK-000002"
    assert list(filas[2][2:]) == ["luis.perez", "Phishing", "Media", "Correo sospechoso."]


def test_generar_ticket_sanitiza_inyeccion_excel(tmp_path, monkeypatch):
    """Verifica que celdas que inicien con prefijos de fórmula se neutralicen."""
    monkeypatch.chdir(tmp_path)

    ruta = generar_ticket("=CMD|'/C calc'!A0", "+Tipo", "@Malicioso", prioridad="Baja")
    wb = load_workbook(ruta)
    ws = wb["Tickets"]
    filas = list(ws.iter_rows(values_only=True))

    assert list(filas[1][2:]) == ["'=CMD|'/C calc'!A0", "'+Tipo", "Baja", "'@Malicioso"]


def test_notificar_webhook_firma_hmac(monkeypatch):
    """Verifica que el webhook firme el payload con HMAC-SHA256 usando WEBHOOK_SECRET."""
    monkeypatch.setenv("WEBHOOK_ALERTA_URL", "https://example.com/webhook")
    monkeypatch.setenv("WEBHOOK_SECRET", "mi_secreto_seguro")

    captura = {}

    def _fake_urlopen(req, timeout=5):
        captura["req"] = req
        cm = MagicMock()
        cm.__enter__.return_value = MagicMock()
        return cm

    monkeypatch.setattr("urllib.request.urlopen", _fake_urlopen)

    _notificar_webhook("TICK-000001", "2026-11-15 16:35:00", "Ana", "Phishing", "Alta", "Correo raro")

    req = captura["req"]
    esperada = hmac.new(b"mi_secreto_seguro", req.data, hashlib.sha256).hexdigest()
    assert req.get_header("X-webhook-signature") == f"sha256={esperada}"
