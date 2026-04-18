from datetime import datetime, timedelta, UTC
import re
from statistics import mean
from app.db import fish_readings_collection, fish_status_collection


def serialize_doc(doc):
    clean = dict(doc)

    clean.pop("sortDate", None)
    clean.pop("canonicalFishId", None)

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
    epoch = datetime(1970, 1, 1, tzinfo=UTC)

    pipeline = [
        {
            "$addFields": {
                "canonicalFishId": {"$ifNull": ["$fishId", "$robotId"]},
                "sortDate": {
                    "$convert": {
                        "input": {"$ifNull": ["$updatedAt", "$timestamp"]},
                        "to": "date",
                        "onError": epoch,
                        "onNull": epoch,
                    }
                },
            }
        },
        {
            "$match": {
                "canonicalFishId": {"$ne": None},
                "sortDate": {"$gte": since},
            }
        },
        {"$sort": {"sortDate": -1}},
        {"$limit": limit},
        {
            "$project": {
                "_id": 1,
                "fishId": 1,
                "robotId": 1,
                "waterBody": 1,
                "timestamp": 1,
                "updatedAt": 1,
                "location": 1,
                "metrics": 1,
                "alert": 1,
                "sortDate": 1,
                "canonicalFishId": 1,
            }
        },
    ]

    docs = fish_readings_collection.aggregate(pipeline)
    return [serialize_doc(doc) for doc in docs]


def _fish_id_variants(fish_id):
    if not fish_id:
        return []

    value = str(fish_id).strip().lower()
    variants = {value}
    match = re.match(r"fish[_-]?0*(\d+)$", value)

    if match:
        num = int(match.group(1))
        variants.add(f"fish_{num:02d}")
        variants.add(f"fish_{num}")

    return sorted(variants)


def get_fish_readings_by_id(fish_id, hours=168, limit=500):
    since = datetime.now(UTC) - timedelta(hours=hours)
    epoch = datetime(1970, 1, 1, tzinfo=UTC)
    id_variants = _fish_id_variants(fish_id)

    pipeline = [
        {
            "$addFields": {
                "canonicalFishId": {"$ifNull": ["$fishId", "$robotId"]},
                "sortDate": {
                    "$convert": {
                        "input": {"$ifNull": ["$updatedAt", "$timestamp"]},
                        "to": "date",
                        "onError": epoch,
                        "onNull": epoch,
                    }
                },
            }
        },
        {
            "$match": {
                "canonicalFishId": {"$in": id_variants},
                "sortDate": {"$gte": since},
            }
        },
        {"$sort": {"sortDate": 1}},
        {"$limit": limit},
        {
            "$project": {
                "_id": 1,
                "fishId": 1,
                "robotId": 1,
                "waterBody": 1,
                "timestamp": 1,
                "updatedAt": 1,
                "location": 1,
                "metrics": 1,
                "alert": 1,
                "sortDate": 1,
                "canonicalFishId": 1,
            }
        },
    ]

    docs = fish_readings_collection.aggregate(pipeline)
    return [serialize_doc(doc) for doc in docs]


def get_current_fish_status(limit=200):
    epoch = datetime(1970, 1, 1, tzinfo=UTC)

    pipeline = [
        {
            "$addFields": {
                "canonicalFishId": {"$ifNull": ["$fishId", "$robotId"]},
                "sortDate": {
                    "$convert": {
                        "input": {"$ifNull": ["$updatedAt", "$timestamp"]},
                        "to": "date",
                        "onError": epoch,
                        "onNull": epoch,
                    }
                },
            }
        },
        {"$match": {"canonicalFishId": {"$ne": None}}},
        {"$sort": {"canonicalFishId": 1, "sortDate": -1}},
        {
            "$group": {
                "_id": "$canonicalFishId",
                "doc": {"$first": "$$ROOT"},
            }
        },
        {"$replaceRoot": {"newRoot": "$doc"}},
        {
            "$project": {
                "_id": 1,
                "fishId": 1,
                "robotId": 1,
                "waterBody": 1,
                "timestamp": 1,
                "updatedAt": 1,
                "location": 1,
                "metrics": 1,
                "alert": 1,
                "sortDate": 1,
            }
        },
        {"$sort": {"sortDate": -1}},
        {"$limit": limit},
    ]

    docs = fish_status_collection.aggregate(pipeline)
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
