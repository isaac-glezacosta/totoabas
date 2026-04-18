from fastapi import APIRouter, HTTPException, Query
from app.models import AskRequest
from app.services.fish_service import get_recent_fish_readings, build_summary
from app.services.gemini_service import generate_report, answer_question

router = APIRouter()


@router.get("/report")
def report(hours: int = Query(24, ge=1, le=168)):
    docs = get_recent_fish_readings(hours=hours, limit=250)
    summary_data = build_summary(docs)

    if summary_data["num_measurements"] == 0:
        raise HTTPException(status_code=404, detail="No hay datos recientes")

    report_text = generate_report(summary_data)
    return {"report": report_text, "summary": summary_data}


@router.post("/ask")
def ask(payload: AskRequest):
    docs = get_recent_fish_readings(hours=payload.hours, limit=250)
    summary_data = build_summary(docs)

    if summary_data["num_measurements"] == 0:
        raise HTTPException(status_code=404, detail="No hay datos para analizar")

    answer = answer_question(payload.question, summary_data)
    return {"answer": answer}