from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app import db
from app.auth import get_current_user
from datetime import datetime
import asyncio   # ✅ NEW

router = APIRouter(prefix="/device", tags=["device"])


# =====================================================
# MODELS
# =====================================================
class DevicePayload(BaseModel):
    deviceId: str
    data: dict


# =====================================================
# POST: Publish device data (manual / HTTP)
# =====================================================
@router.post("/publish")
async def publish(payload: DevicePayload, user=Depends(get_current_user)):
    doc = {
        "deviceId": payload.deviceId,
        "data": payload.data,
        "ts": datetime.utcnow(),
        "published_by": user["_id"],
    }
    res = await db.devices_coll.insert_one(doc)
    return {"_id": str(res.inserted_id)}


# =====================================================
# GET: Device telemetry stream (for frontend)
# =====================================================
@router.get("/stream")
async def get_device_stream(limit: int = 50):
    cursor = (
        db.devices_coll
        .find()
        .sort("_id", -1)
        .limit(limit)
    )

    items = []
    async for doc in cursor:
        telemetry = doc.get("data", {})

        items.append({
            "_id": str(doc["_id"]),
            "deviceId": doc.get("deviceId"),

            # 🔥 Flatten telemetry fields
            "Battery_Level": telemetry.get("Battery_Level"),
            "First_Sensor_temperature": telemetry.get("First_Sensor_temperature"),
            "Humidity": telemetry.get("Humidity"),
            "Route_From": telemetry.get("Route_From"),
            "Route_To": telemetry.get("Route_To"),
            "Timestamp": telemetry.get("Timestamp"),

            "ts": doc.get("ts"),
        })

    return items



# =====================================================
# BACKGROUND SOCKET / INGEST LOOP
# (Started from main.py using asyncio.create_task)
# =====================================================
async def socket_ingest_loop():
    """
    Background task for future socket / Kafka ingestion.
    Currently non-blocking and safe.
    """
    while True:
        # 🔧 Placeholder (can be replaced with socket/Kafka logic)
        # NEVER use time.sleep() in async code
        await asyncio.sleep(5)
