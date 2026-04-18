from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from app.models import AskRequest
from app.services.fish_service import (
    get_recent_fish_readings,
    get_current_fish_status,
    build_summary,
)
from app.services.gemini_service import (
    generate_report,
    answer_question,
    GeminiServiceError,
)

router = APIRouter()


def _build_local_report(summary_data: dict, reason: Optional[str] = None) -> str:
    def metric_line(name: str, metric_data: Optional[dict], unit: str = "") -> str:
        if not metric_data:
            return f"- {name}: sin datos"

        avg = metric_data.get("avg")
        min_value = metric_data.get("min")
        max_value = metric_data.get("max")
        return (
            f"- {name}: promedio {avg}{unit}, minimo {min_value}{unit}, maximo {max_value}{unit}"
        )

    fishes = ", ".join(summary_data.get("fishes", [])) or "sin registros"
    water_bodies = ", ".join(summary_data.get("water_bodies", [])) or "sin registros"

    lines = [
        "REPORTE DE CALIDAD DE AGUA (FALLBACK LOCAL)",
        "",
        "1. Resumen ejecutivo",
        (
            f"Se analizaron {summary_data.get('num_measurements', 0)} mediciones "
            f"de {len(summary_data.get('fishes', []))} pez(es) en "
            f"{len(summary_data.get('water_bodies', []))} cuerpo(s) de agua."
        ),
        f"Peces observados: {fishes}",
        f"Cuerpos de agua observados: {water_bodies}",
        "",
        "2. Hallazgos clave",
        metric_line("Temperatura", summary_data.get("temperature"), " C"),
        metric_line("pH", summary_data.get("ph")),
        metric_line("Turbidez", summary_data.get("turbidity"), " NTU"),
        metric_line("Oxigeno disuelto", summary_data.get("oxygen"), " mg/L"),
        f"- Alertas detectadas: {summary_data.get('alerts_count', 0)}",
        "",
        "3. Riesgos o anomalias",
        "- Se recomienda revisar peces con estado Contaminada o Aceptable para confirmar tendencia.",
        "- Si hay incrementos de turbidez y caidas de oxigeno, priorizar inspeccion fisica.",
        "",
        "4. Recomendaciones",
        "- Mantener monitoreo cada hora y registrar eventos de lluvia o descargas.",
        "- Validar calibracion de sensores de pH y oxigeno semanalmente.",
        "- Atender de inmediato cualquier alerta critica sostenida.",
    ]

    if reason:
        lines.extend(["", f"Nota tecnica: Gemini no disponible ({reason})."])

    return "\n".join(lines)


def _build_report_response(hours: int):
    docs = get_recent_fish_readings(hours=hours, limit=250)

    # Fallback: when there are no recent readings, use current fish status so
    # the report endpoint can still answer the frontend with available data.
    if not docs:
        docs = get_current_fish_status(limit=250)

    summary_data = build_summary(docs)

    if summary_data["num_measurements"] == 0:
        raise HTTPException(status_code=404, detail="No hay datos recientes ni estado actual")

    try:
        report_text = generate_report(summary_data)
        return {
            "report": report_text,
            "summary": summary_data,
            "provider": "gemini",
            "model": "gemini-2.5-flash",
        }
    except GeminiServiceError as exc:
        # Keep report endpoint available even when Gemini credentials/project access fail.
        return {
            "report": _build_local_report(summary_data, str(exc)),
            "summary": summary_data,
            "provider": "local-fallback",
            "model": "rule-based-v1",
            "warning": str(exc),
        }


@router.get("/report")
def report(hours: int = Query(24, ge=1, le=168)):
    return _build_report_response(hours)


@router.get("/report/gemini")
def report_gemini(hours: int = Query(24, ge=1, le=168)):
    return _build_report_response(hours)


@router.post("/ask")
def ask(payload: AskRequest):
    docs = get_recent_fish_readings(hours=payload.hours, limit=250)

    if not docs:
        docs = get_current_fish_status(limit=250)

    summary_data = build_summary(docs)

    if summary_data["num_measurements"] == 0:
        raise HTTPException(status_code=404, detail="No hay datos para analizar")

    try:
        answer = answer_question(payload.question, summary_data)
    except GeminiServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return {"answer": answer}