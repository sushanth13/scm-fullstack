import os
from pathlib import Path

from dotenv import load_dotenv
from pymongo import MongoClient


BACKEND_DIR = Path(__file__).resolve().parent
load_dotenv(BACKEND_DIR / ".env", override=True)


def main():
    client = MongoClient(os.getenv("MONGO_URL"))
    db = client[os.getenv("DB_NAME", "scmxpertlite")]
    devices = db["devices"]

    updated = 0

    for doc in devices.find():
        raw_timestamp = doc.get("ts") or doc.get("Timestamp")
        if raw_timestamp is None:
            raw_timestamp = doc["_id"].generation_time.timestamp()

        update = {
            "Timestamp": raw_timestamp,
            "ts": raw_timestamp,
        }
        result = devices.update_one({"_id": doc["_id"]}, {"$set": update})
        if result.modified_count:
            updated += 1

    print(f"Updated timestamp fields on {updated} device records")


if __name__ == "__main__":
    main()
