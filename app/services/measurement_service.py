from datetime import datetime, timedelta, UTC
from statistics import mean
from app.db import collection


def serialize_doc(doc):
    clean = dict(doc)
    if "_id" in clean:
        clean["_id"] = str(clean["_id"])
    if "timestamp" in clean:
        clean["timestamp"] = clean["timestamp"].isoformat()
    return clean


def get_recent_measurements(hours=24, limit=200):
    since = datetime.now(UTC) - timedelta(hours=hours)

    docs = collection.find(
        {"timestamp": {"$gte": since}},
        {
            "_id": 1,
            "robotId": 1,
            "waterBody": 1,
            "timestamp": 1,
            "location": 1,
            "metrics": 1,
            "alert": 1,
        }
    ).sort("timestamp", -1).limit(limit)

    return [serialize_doc(doc) for doc in docs]


def build_summary(docs):
    if not docs:
        return {
            "num_measurements": 0,
            "robots": [],
            "water_bodies": [],
            "temperature": None,
            "ph": None,
            "turbidity": None,
            "oxygen": None,
            "alerts_count": 0,
            "sample_records": [],
        }

    temps, phs, turbs, oxys = [], [], [], []
    robots, water_bodies = set(), set()
    alerts_count = 0

    for d in docs:
        robots.add(d.get("robotId", "unknown"))
        water_bodies.add(d.get("waterBody", "unknown"))

        metrics = d.get("metrics", {})

        if isinstance(metrics.get("temperature"), (int, float)):
            temps.append(metrics["temperature"])
        if isinstance(metrics.get("ph"), (int, float)):
            phs.append(metrics["ph"])
        if isinstance(metrics.get("turbidity"), (int, float)):
            turbs.append(metrics["turbidity"])
        if isinstance(metrics.get("oxygen"), (int, float)):
            oxys.append(metrics["oxygen"])

        if d.get("alert") is True:
            alerts_count += 1

    def stats(values):
        if not values:
            return None
        return {
            "avg": round(mean(values), 2),
            "min": round(min(values), 2),
            "max": round(max(values), 2),
        }

    return {
        "num_measurements": len(docs),
        "robots": sorted(robots),
        "water_bodies": sorted(water_bodies),
        "temperature": stats(temps),
        "ph": stats(phs),
        "turbidity": stats(turbs),
        "oxygen": stats(oxys),
        "alerts_count": alerts_count,
        "sample_records": docs[:10],
    }