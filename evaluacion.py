"""Script de evaluación automática para el agente de soporte de TI."""

import csv
import json
import os
import sys
import time
from pathlib import Path

# Frases clave en minúsculas usadas para detectar cuando el bot rechaza
# cortésmente consultas que no pertenecen al dominio de soporte de TI.
FRASES_RECHAZO: list[str] = [
    "solo atiendo",
    "únicamente atiendo",
    "no puedo ayudar",
    "fuera de mi alcance",
    "únicamente soporte",
    "solo puedo ayudar",
    "únicamente temas de",
    "fuera de mi ámbito",
    "solo respondo",
    "no está relacionada con ti",
    "no corresponde a soporte",
]

BASE_DIR = Path(__file__).resolve().parent


def detectar_rechazo(respuesta: str) -> bool:
    """Indica si la respuesta contiene alguna frase de rechazo temático."""
    texto = respuesta.lower()
    return any(frase in texto for frase in FRASES_RECHAZO)


def verificar_api_key() -> None:
    """Valida que GROQ_API_KEY esté configurada; de lo contrario termina sin traceback."""
    if not os.environ.get("GROQ_API_KEY"):
        print(
            "Error: No se encontró la variable de entorno GROQ_API_KEY.\n"
            "Por favor configúrela en su terminal antes de ejecutar la evaluación:\n"
            '  PowerShell: $env:GROQ_API_KEY="tu_clave_aqui"\n'
            '  Bash/Zsh:   export GROQ_API_KEY="tu_clave_aqui"'
        )
        sys.exit(1)


def ejecutar_evaluacion() -> None:
    """Ejecuta todos los casos de prueba y guarda resultados y métricas."""
    verificar_api_key()

    if str(BASE_DIR) not in sys.path:
        sys.path.insert(0, str(BASE_DIR))

    import agente_ia  # noqa: E402

    ruta_casos = BASE_DIR / "eval" / "casos.csv"
    ruta_results_dir = BASE_DIR / "results"
    ruta_results_dir.mkdir(parents=True, exist_ok=True)

    with open(ruta_casos, mode="r", encoding="utf-8", newline="") as f:
        casos = list(csv.DictReader(f))

    resultados: list[dict[str, object]] = []
    tiempos: list[float] = []
    aciertos_tematicos = 0
    casos_debe_escalar = 0
    escalamientos_correctos = 0

    for caso in casos:
        consulta = caso["consulta"]
        es_ti = caso["es_ti"].strip().lower()
        debe_escalar = caso["debe_escalar"].strip().lower()

        inicio = time.perf_counter()
        respuesta, escalo = agente_ia.consultar(consulta)
        duracion = time.perf_counter() - inicio
        tiempos.append(duracion)

        rechazo_detectado = detectar_rechazo(respuesta)
        acierto_tematico = (es_ti == "si" and not rechazo_detectado) or (
            es_ti == "no" and rechazo_detectado
        )
        if acierto_tematico:
            aciertos_tematicos += 1

        if debe_escalar == "si":
            casos_debe_escalar += 1
            if escalo:
                escalamientos_correctos += 1

        resultados.append(
            {
                "id": caso["id"],
                "consulta": consulta,
                "es_ti": es_ti,
                "debe_escalar": debe_escalar,
                "respuesta": respuesta,
                "escalo": escalo,
                "rechazo_detectado": rechazo_detectado,
                "acierto_tematico": acierto_tematico,
                "tiempo_seg": round(duracion, 4),
            }
        )

    total_casos = len(casos)
    tiempo_promedio_seg = round(sum(tiempos) / total_casos, 4) if total_casos else 0.0
    precision_tematica = (
        round(aciertos_tematicos / total_casos, 4) if total_casos else 0.0
    )
    exactitud_escalamiento = (
        round(escalamientos_correctos / casos_debe_escalar, 4)
        if casos_debe_escalar
        else 0.0
    )

    ruta_resultados_csv = ruta_results_dir / "resultados.csv"
    columnas_salida = [
        "id",
        "consulta",
        "es_ti",
        "debe_escalar",
        "respuesta",
        "escalo",
        "rechazo_detectado",
        "acierto_tematico",
        "tiempo_seg",
    ]
    with open(ruta_resultados_csv, mode="w", encoding="utf-8", newline="") as f:
        escritor = csv.DictWriter(f, fieldnames=columnas_salida)
        escritor.writeheader()
        escritor.writerows(resultados)

    metricas = {
        "total_casos": total_casos,
        "tiempo_promedio_seg": tiempo_promedio_seg,
        "precision_tematica": precision_tematica,
        "exactitud_escalamiento": exactitud_escalamiento,
        "casos_debe_escalar": casos_debe_escalar,
        "escalamientos_correctos": escalamientos_correctos,
    }
    ruta_metricas_json = ruta_results_dir / "metricas.json"
    with open(ruta_metricas_json, mode="w", encoding="utf-8") as f:
        json.dump(metricas, f, ensure_ascii=False, indent=2)

    print("=== Resumen de Evaluación ===")
    print(f"Total de casos:           {total_casos}")
    print(f"Tiempo promedio (seg):    {tiempo_promedio_seg:.4f}")
    print(f"Precisión temática:       {precision_tematica:.2%} ({aciertos_tematicos}/{total_casos})")
    print(
        f"Exactitud escalamiento:   {exactitud_escalamiento:.2%} "
        f"({escalamientos_correctos}/{casos_debe_escalar})"
    )
    print(f"Resultados guardados en:  {ruta_resultados_csv}")
    print(f"Métricas guardadas en:    {ruta_metricas_json}")


if __name__ == "__main__":
    ejecutar_evaluacion()
