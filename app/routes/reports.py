from fastapi import APIRouter, HTTPException, Query
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


def _local_report(summary_data: dict, reason: str | None = None) -> str:
    num = summary_data.get("num_measurements", 0)
    alerts = summary_data.get("alerts_count", 0)
    fishes = summary_data.get("fishes") or []
    water_bodies = summary_data.get("water_bodies") or []

    ph = summary_data.get("ph")
    oxygen = summary_data.get("oxygen")
    turbidity = summary_data.get("turbidity")

    def stats_line(label: str, stats: dict | None, unit: str) -> str:
        if not stats:
            return f"- {label}: sin datos"
        return (
            f"- {label}: avg {stats.get('avg', 'N/D')}{unit}, "
            f"min {stats.get('min', 'N/D')}{unit}, max {stats.get('max', 'N/D')}{unit}"
        )

    risk = "Bajo"
    if alerts > 0:
        risk = "Medio"
    if alerts >= max(2, int(max(num, 1) * 0.25)):
        risk = "Alto"

    lines = [
        "Reporte operativo (fallback local)",
        "",
        "1. Resumen ejecutivo",
        f"- Mediciones analizadas: {num}",
        f"- Peces con datos: {len(fishes)}",
        f"- Cuerpos de agua: {', '.join(water_bodies) if water_bodies else 'N/D'}",
        f"- Alertas detectadas: {alerts}",
        f"- Riesgo global estimado: {risk}",
        "",
        "2. Hallazgos clave",
        stats_line("pH", ph, ""),
        stats_line("Oxigeno", oxygen, " mg/L"),
        stats_line("Turbidez", turbidity, " NTU"),
        "",
        "3. Riesgos o anomalias",
        "- Revisar peces con bandera de alerta para confirmar persistencia.",
        "- Priorizar tramos con mayor turbidez y menor oxigeno.",
        "",
        "4. Recomendaciones",
        "- Mantener monitoreo continuo cada 1 hora en tramos criticos.",
        "- Ejecutar inspeccion visual en puntos con alertas repetidas.",
        "- Generar nuevo reporte despues de la siguiente corrida de datos.",
    ]

    if reason:
        lines.extend(["", f"Nota tecnica: Gemini no disponible ({reason})."])

    return "\n".join(lines)


def _build_report_response(hours: int, force_gemini: bool = False):
    docs = get_recent_fish_readings(hours=hours, limit=250)

    # Fallback: when there are no recent readings, use current fish status so
    # the report endpoint can still answer the frontend with available data.
    if not docs:
        docs = get_current_fish_status(limit=250)

    summary_data = build_summary(docs)

    if summary_data["num_measurements"] == 0:
        raise HTTPException(status_code=404, detail="No hay datos recientes ni estado actual")

    warning = None
    source = "gemini"

    try:
        report_text = generate_report(summary_data)
    except GeminiServiceError as exc:
        if force_gemini:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        report_text = _local_report(summary_data, str(exc))
        warning = str(exc)
        source = "local_fallback"

    return {
        "report": report_text,
        "summary": summary_data,
        "report_source": source,
        "report_warning": warning,
    }


@router.get("/report")
def report(hours: int = Query(24, ge=1, le=168)):
    return _build_report_response(hours, force_gemini=False)


@router.get("/report/gemini")
def report_gemini(hours: int = Query(24, ge=1, le=168)):
    return _build_report_response(hours, force_gemini=True)


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