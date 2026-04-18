    import random
from datetime import datetime, UTC
from fastapi import APIRouter, Query
from app.db import collection
from app.services.measurement_service import serialize_doc, get_recent_measurements, build_summary

router = APIRouter()

@router.get("/latest")
def latest_measurements(
    hours: int = Query(24, ge=1, le=168),
    limit: int = Query(50, ge=1, le=500)
):
    docs = get_recent_measurements(hours=hours, limit=limit)
    return {"count": len(docs), "data": docs}


@router.get("/summary")
def summary(hours: int = Query(24, ge=1, le=168)):
    docs = get_recent_measurements(hours=hours, limit=500)
    return build_summary(docs)

@router.post("/simulate")
def simulate():
    doc = {
        "robotId": "fish_01",
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

    result = collection.insert_one(doc)

    return {
        "inserted_id": str(result.inserted_id),
        "doc": serialize_doc(doc)
    }