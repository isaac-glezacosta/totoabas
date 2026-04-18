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


@router.get("/report")
def report(hours: int = Query(24, ge=1, le=168)):
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
    except GeminiServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return {"report": report_text, "summary": summary_data}


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