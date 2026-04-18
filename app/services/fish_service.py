from datetime import datetime, timedelta, UTC
from statistics import mean
from app.db import fish_readings_collection, fish_status_collection


def serialize_doc(doc):
    clean = dict(doc)

    # Backward compatibility with legacy schema where fish id is stored as robotId.
    if "fishId" not in clean and "robotId" in clean:
        clean["fishId"] = clean["robotId"]

    # Normalize status timestamp field when legacy docs store it as timestamp.
    if "updatedAt" not in clean and "timestamp" in clean:
        clean["updatedAt"] = clean["timestamp"]

    if "_id" in clean:
        clean["_id"] = str(clean["_id"])
    if "timestamp" in clean and hasattr(clean["timestamp"], "isoformat"):
        clean["timestamp"] = clean["timestamp"].isoformat()
    if "updatedAt" in clean and hasattr(clean["updatedAt"], "isoformat"):
        clean["updatedAt"] = clean["updatedAt"].isoformat()
    return clean


def get_recent_fish_readings(hours=24, limit=200):
    since = datetime.now(UTC) - timedelta(hours=hours)
    since_iso = since.isoformat()

    docs = fish_readings_collection.find(
        {
            "$or": [
                {"timestamp": {"$gte": since}},
                {"updatedAt": {"$gte": since}},
                {"timestamp": {"$gte": since_iso}},
                {"updatedAt": {"$gte": since_iso}},
            ]
        },
        {
            "_id": 1,
            "fishId": 1,
            "robotId": 1,
            "waterBody": 1,
            "timestamp": 1,
            "updatedAt": 1,
            "location": 1,
            "metrics": 1,
            "alert": 1,
        },
    ).sort("timestamp", -1).limit(limit)

    return [serialize_doc(doc) for doc in docs]


def get_current_fish_status(limit=200):
    docs = fish_status_collection.find(
        {},
        {
            "_id": 1,
            "fishId": 1,
            "robotId": 1,
            "waterBody": 1,
            "timestamp": 1,
            "updatedAt": 1,
            "location": 1,
            "metrics": 1,
            "alert": 1,
        },
    ).sort("updatedAt", -1).limit(limit)

    return [serialize_doc(doc) for doc in docs]


def get_fish_status_by_id(fish_id):
    doc = fish_status_collection.find_one(
        {"$or": [{"fishId": fish_id}, {"robotId": fish_id}]},
        {
            "_id": 1,
            "fishId": 1,
            "robotId": 1,
            "waterBody": 1,
            "timestamp": 1,
            "updatedAt": 1,
            "location": 1,
            "metrics": 1,
            "alert": 1,
        },
    )

    if not doc:
        return None

    return serialize_doc(doc)


def write_fish_reading_and_status(doc):
    reading_doc = dict(doc)

    # Keep robotId mirrored for compatibility with existing data consumers.
    if "robotId" not in reading_doc and "fishId" in reading_doc:
        reading_doc["robotId"] = reading_doc["fishId"]

    fish_readings_collection.insert_one(reading_doc)

    status_doc = {
        "fishId": doc["fishId"],
        "robotId": doc["fishId"],
        "waterBody": doc.get("waterBody"),
        "timestamp": doc.get("timestamp", datetime.now(UTC)),
        "updatedAt": doc.get("timestamp", datetime.now(UTC)),
        "location": doc.get("location"),
        "metrics": doc.get("metrics", {}),
        "alert": doc.get("alert", False),
    }

    fish_status_collection.update_one(
        {"fishId": status_doc["fishId"]},
        {"$set": status_doc},
        upsert=True,
    )

    return serialize_doc(reading_doc)


def build_summary(docs):
    if not docs:
        return {
            "num_measurements": 0,
            "fishes": [],
            "water_bodies": [],
            "temperature": None,
            "ph": None,
            "turbidity": None,
            "oxygen": None,
            "alerts_count": 0,
            "sample_records": [],
        }

    temps, phs, turbs, oxys = [], [], [], []
    fishes, water_bodies = set(), set()
    alerts_count = 0

    for d in docs:
        fishes.add(d.get("fishId", "unknown"))
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
        "fishes": sorted(fishes),
        "water_bodies": sorted(water_bodies),
        "temperature": stats(temps),
        "ph": stats(phs),
        "turbidity": stats(turbs),
        "oxygen": stats(oxys),
        "alerts_count": alerts_count,
        "sample_records": docs[:10],
    }
