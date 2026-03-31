import os
import hashlib
from pathlib import Path

from dotenv import load_dotenv
from pymongo import MongoClient


BACKEND_DIR = Path(__file__).resolve().parent
load_dotenv(BACKEND_DIR / ".env", override=True)


def stable_offset(seed: str) -> float:
    digest = hashlib.sha256(seed.encode("utf-8")).digest()
    return (digest[0] / 255.0) * 10.0 - 5.0


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def pick_existing_humidity(doc: dict):
    data = doc.get("data")
    if isinstance(data, dict):
        for key in ("Humidity", "humidity"):
            value = data.get(key)
            if value is not None:
                return value

    for key in ("Humidity", "humidity"):
        value = doc.get(key)
        if value is not None:
            return value

    return None


def synthesize_humidity(doc: dict) -> float:
    seed = str(doc.get("_id") or doc.get("Device_ID") or doc.get("deviceId") or "device")
    temperature = doc.get("First_Sensor_temperature")

    if isinstance(temperature, (int, float)):
        base = 78.0 - (float(temperature) * 0.8)
    else:
        base = 58.0

    humidity = clamp(base + stable_offset(seed), 40.0, 80.0)
    return round(humidity, 1)


def main():
    client = MongoClient(os.getenv("MONGO_URL"))
    db = client[os.getenv("DB_NAME", "scmxpertlite")]
    devices = db["devices"]

    updated = 0
    copied = 0
    synthesized = 0

    for doc in devices.find():
        humidity = pick_existing_humidity(doc)
        if humidity is not None:
            update = {"Humidity": humidity}
            if isinstance(doc.get("data"), dict):
                update["data.Humidity"] = humidity
            result = devices.update_one({"_id": doc["_id"]}, {"$set": update})
            if result.modified_count:
                copied += 1
                updated += 1
            continue

        humidity = synthesize_humidity(doc)
        update = {"Humidity": humidity}
        if isinstance(doc.get("data"), dict):
            update["data.Humidity"] = humidity
        result = devices.update_one({"_id": doc["_id"]}, {"$set": update})
        if result.modified_count:
            synthesized += 1
            updated += 1

    print(
        f"Updated {updated} device records "
        f"(copied existing humidity: {copied}, synthesized humidity: {synthesized})"
    )


if __name__ == "__main__":
    main()
