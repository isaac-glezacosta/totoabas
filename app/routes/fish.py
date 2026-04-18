import random
from datetime import datetime, UTC
from fastapi import APIRouter, HTTPException, Query
from app.services.fish_service import (
    get_recent_fish_readings,
    get_current_fish_status,
    get_fish_status_by_id,
    build_summary,
    write_fish_reading_and_status,
)

router = APIRouter()


@router.get("/fish_readings/latest")
def latest_fish_readings(
    hours: int = Query(24, ge=1, le=168),
    limit: int = Query(50, ge=1, le=500),
):
    docs = get_recent_fish_readings(hours=hours, limit=limit)
    return {"count": len(docs), "data": docs}


@router.get("/fish_readings/summary")
def fish_readings_summary(hours: int = Query(24, ge=1, le=168)):
    docs = get_recent_fish_readings(hours=hours, limit=500)
    return build_summary(docs)


@router.get("/fish_status")
def list_current_fish_status(limit: int = Query(100, ge=1, le=500)):
    docs = get_current_fish_status(limit=limit)
    return {"count": len(docs), "data": docs}


@router.get("/fish_status/{fish_id}")
def current_fish_status(fish_id: str):
    doc = get_fish_status_by_id(fish_id)
    if not doc:
        raise HTTPException(status_code=404, detail="No hay estado actual para ese pez")
    return doc


@router.post("/fish_readings/simulate")
def simulate_fish_reading():
    fish_id = f"fish_{random.randint(1, 10):02d}"
    doc = {
        "fishId": fish_id,
        "waterBody": "presa_centro",
        "timestamp": datetime.now(UTC),
        "location": {"lat": 20.59, "lng": -100.39},
        "metrics": {
            "temperature": round(random.uniform(18, 30), 2),
            "ph": round(random.uniform(6.2, 8.8), 2),
            "turbidity": round(random.uniform(1, 12), 2),
            "oxygen": round(random.uniform(3.5, 8), 2),
        },
    }

    doc["alert"] = (
        doc["metrics"]["ph"] < 6.5
        or doc["metrics"]["ph"] > 8.5
        or doc["metrics"]["oxygen"] < 4
    )

    inserted_doc = write_fish_reading_and_status(doc)
    return {"doc": inserted_doc}
