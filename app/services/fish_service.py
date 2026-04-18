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


def _parse_doc_datetime(value):
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)

    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return None

        normalized = raw.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(normalized)
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
        except ValueError:
            pass

        # Fallback for strings that include microseconds but no timezone.
        if "T" in raw:
            raw_no_tz = re.sub(r"(Z|[+-]\d{2}:\d{2})$", "", raw)
            try:
                parsed = datetime.fromisoformat(raw_no_tz)
                return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed
            except ValueError:
                return None

    return None


def _reading_datetime(doc):
    return _parse_doc_datetime(doc.get("updatedAt")) or _parse_doc_datetime(doc.get("timestamp"))


def _fish_readings_projection():
    return {
        "_id": 1,
        "fishId": 1,
        "robotId": 1,
        "waterBody": 1,
        "timestamp": 1,
        "updatedAt": 1,
        "location": 1,
        "metrics": 1,
        "alert": 1,
    }


def get_recent_fish_readings(hours=24, limit=200):
    since = datetime.now(UTC) - timedelta(hours=hours)
    fetch_cap = min(max(limit * 8, 2000), 50000)
    docs = fish_readings_collection.find({}, _fish_readings_projection()).sort("_id", -1).limit(fetch_cap)
    serialized = [serialize_doc(doc) for doc in docs]

    filtered = []
    for doc in serialized:
        if not (doc.get("fishId") or doc.get("robotId")):
            continue
        reading_dt = _reading_datetime(doc)
        if reading_dt and reading_dt >= since:
            filtered.append((reading_dt, doc))

    filtered.sort(key=lambda item: item[0], reverse=True)
    if filtered:
        return [doc for _, doc in filtered[:limit]]

    # Fallback for datasets with non-parseable or inconsistent timestamp formats.
    docs_no_window = fish_readings_collection.find(
        {
            "$or": [
                {"fishId": {"$exists": True}},
                {"robotId": {"$exists": True}},
            ]
        },
        _fish_readings_projection(),
    ).sort("_id", -1).limit(limit)
    return [serialize_doc(doc) for doc in docs_no_window]


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
    id_variants = _fish_id_variants(fish_id)

    fetch_cap = min(max(limit * 8, 2000), 50000)
    docs = fish_readings_collection.find(
        {
            "$or": [
                {"fishId": {"$in": id_variants}},
                {"robotId": {"$in": id_variants}},
            ]
        },
        _fish_readings_projection(),
    ).sort("_id", -1).limit(fetch_cap)

    serialized = [serialize_doc(doc) for doc in docs]

    filtered = []
    for doc in serialized:
        reading_dt = _reading_datetime(doc)
        if reading_dt and reading_dt >= since:
            filtered.append((reading_dt, doc))

    filtered.sort(key=lambda item: item[0])
    if filtered:
        if len(filtered) > limit:
            filtered = filtered[-limit:]
        return [doc for _, doc in filtered]

    # Fallback for fish history when timestamp parsing/window filtering drops rows.
    docs_no_window = fish_readings_collection.find(
        {
            "$or": [
                {"fishId": {"$in": id_variants}},
                {"robotId": {"$in": id_variants}},
            ]
        },
        _fish_readings_projection(),
    ).sort("_id", -1).limit(limit)

    serialized_no_window = [serialize_doc(doc) for doc in docs_no_window]
    serialized_no_window.reverse()
    return serialized_no_window


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
