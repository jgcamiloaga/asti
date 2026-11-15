"""Módulo de automatización para la generación de tickets de soporte en Excel (.xlsx)."""

import hashlib
import hmac
import json
import logging
import math
import os
import threading
import urllib.error
import urllib.request
from datetime import datetime

logger = logging.getLogger(__name__)

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.worksheet import Worksheet

_TICKET_LOCK = threading.Lock()
_PREFIJOS_FORMULA = ("=", "+", "-", "@", "\t", "\r")
_ENCABEZADOS = ["ID", "Fecha / Hora", "Usuario", "Categoría", "Prioridad", "Descripción"]
_ANCHOS_COLUMNA = {
    "A": 16,
    "B": 20,
    "C": 20,
    "D": 26,
    "E": 14,
    "F": 62,
}

_BORDE_FINO = Border(
    left=Side(style="thin", color="D9E1F2"),
    right=Side(style="thin", color="D9E1F2"),
    top=Side(style="thin", color="D9E1F2"),
    bottom=Side(style="thin", color="D9E1F2"),
)
_FILL_HEADER = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
_FONT_HEADER = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
_FILL_FILA_PAR = PatternFill(start_color="F7F9FC", end_color="F7F9FC", fill_type="solid")
_FONT_DATO = Font(name="Calibri", size=10, color="1F2937")

_ESTILOS_PRIORIDAD = {
    "Alta": (
        PatternFill(start_color="FADBD8", end_color="FADBD8", fill_type="solid"),
        Font(name="Calibri", size=10, bold=True, color="922B21"),
    ),
    "Media": (
        PatternFill(start_color="FCF3CF", end_color="FCF3CF", fill_type="solid"),
        Font(name="Calibri", size=10, bold=True, color="9A7D0A"),
    ),
    "Baja": (
        PatternFill(start_color="D5F5E3", end_color="D5F5E3", fill_type="solid"),
        Font(name="Calibri", size=10, bold=True, color="1E8449"),
    ),
}


def _sanitizar_celda(valor: str) -> str:
    """Neutraliza posible Formula Injection anteponiendo apóstrofe si aplica."""
    if valor and valor.startswith(_PREFIJOS_FORMULA):
        return f"'{valor}"
    return valor


def _inicializar_hoja(ws: Worksheet) -> None:
    """Configura encabezados, anchos de columna, filtros y panel inmovilizado."""
    ws.title = "Tickets"
    ws.append(_ENCABEZADOS)
    ws.row_dimensions[1].height = 26
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = "A1:F1"

    for col_idx in range(1, len(_ENCABEZADOS) + 1):
        celda = ws.cell(row=1, column=col_idx)
        celda.fill = _FILL_HEADER
        celda.font = _FONT_HEADER
        celda.alignment = Alignment(horizontal="center", vertical="center")
        celda.border = _BORDE_FINO

    for col_letra, ancho in _ANCHOS_COLUMNA.items():
        ws.column_dimensions[col_letra].width = ancho


def _estilizar_fila(ws: Worksheet, fila: int, prioridad: str, descripcion: str) -> None:
    """Aplica bordes, sombreado alterno, ajuste de texto y color de prioridad."""
    es_par = fila % 2 == 0
    for col_idx in range(1, len(_ENCABEZADOS) + 1):
        celda = ws.cell(row=fila, column=col_idx)
        celda.border = _BORDE_FINO
        celda.font = _FONT_DATO
        if es_par:
            celda.fill = _FILL_FILA_PAR

        if col_idx in (1, 2, 5):
            celda.alignment = Alignment(horizontal="center", vertical="center")
        else:
            celda.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)

    celda_prio = ws.cell(row=fila, column=5)
    if prioridad in _ESTILOS_PRIORIDAD:
        fill_prio, font_prio = _ESTILOS_PRIORIDAD[prioridad]
        celda_prio.fill = fill_prio
        celda_prio.font = font_prio

    lineas_aprox = max(1, math.ceil(len(descripcion) / 56))
    ws.row_dimensions[fila].height = max(22, lineas_aprox * 16 + 6)


def generar_ticket(
    usuario: str,
    tipo: str,
    descripcion: str,
    prioridad: str = "Media",
) -> str:
    """Registra un ticket en el archivo Excel diario ``tickets/tickets_YYYY-MM-DD.xlsx``.

    Si el archivo del día ya existe, reutiliza la misma hoja ``Tickets`` y
    asigna el siguiente ID secuencial ``TICK-000XXX``.

    Args:
        usuario: Identificador o nombre del usuario que reporta el incidente.
        tipo: Categoría del incidente clasificada por el agente.
        descripcion: Descripción original escrita por el usuario.
        prioridad: Nivel de prioridad (``Baja``, ``Media`` o ``Alta``).

    Returns:
        Ruta relativa del archivo Excel del día.
    """
    os.makedirs("tickets", exist_ok=True)

    ahora = datetime.now()
    ruta_archivo = os.path.join("tickets", f"tickets_{ahora.strftime('%Y-%m-%d')}.xlsx")
    timestamp = ahora.strftime("%Y-%m-%d %H:%M:%S")
    prioridad_norm = prioridad if prioridad in _ESTILOS_PRIORIDAD else "Media"
    desc_sanitizada = _sanitizar_celda(descripcion)

    with _TICKET_LOCK:
        if os.path.exists(ruta_archivo):
            wb = load_workbook(ruta_archivo)
            ws = wb["Tickets"] if "Tickets" in wb.sheetnames else wb.active
        else:
            wb = Workbook()
            ws = wb.active
            _inicializar_hoja(ws)

        siguiente_num = max(1, ws.max_row)
        ticket_id = f"TICK-{siguiente_num:06d}"

        ws.append(
            [
                ticket_id,
                timestamp,
                _sanitizar_celda(usuario),
                _sanitizar_celda(tipo),
                prioridad_norm,
                desc_sanitizada,
            ]
        )
        _estilizar_fila(ws, ws.max_row, prioridad_norm, desc_sanitizada)

        wb.save(ruta_archivo)

    _notificar_webhook(ticket_id, timestamp, usuario, tipo, prioridad_norm, descripcion)
    return ruta_archivo


def _notificar_webhook(
    ticket_id: str,
    timestamp: str,
    usuario: str,
    categoria: str,
    prioridad: str,
    descripcion: str,
) -> None:
    """Envía una alerta JSON a `WEBHOOK_ALERTA_URL` si está configurada."""
    url = os.environ.get("WEBHOOK_ALERTA_URL", "").strip()
    if not url or not url.startswith(("https://", "http://")):
        return

    payload = json.dumps(
        {
            "ticket_id": ticket_id,
            "timestamp": timestamp,
            "usuario": usuario,
            "categoria": categoria,
            "prioridad": prioridad,
            "descripcion": descripcion,
        }
    ).encode("utf-8")

    headers = {"Content-Type": "application/json"}
    secret = os.environ.get("WEBHOOK_SECRET", "").strip()
    if secret:
        firma = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
        headers["X-Webhook-Signature"] = f"sha256={firma}"

    req = urllib.request.Request(
        url,
        data=payload,
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=5):
            pass
    except (urllib.error.URLError, TimeoutError) as exc:
        logger.warning("No se pudo enviar alerta al webhook: %s", exc)
