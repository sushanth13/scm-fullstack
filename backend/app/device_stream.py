from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app import db
from app.auth import get_current_user
from datetime import datetime
import asyncio
import logging

router = APIRouter(prefix="/device", tags=["device"])
logger = logging.getLogger("scmxpertlite.device")

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
# GET: Device telemetry (frontend)
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
        doc["_id"] = str(doc["_id"])
        items.append(doc)

    return items

# =====================================================
# BACKGROUND DEVICE STREAM
# =====================================================
async def start_device_stream():
    """
    Background task started on app startup.
    Can later be extended to:
    - Kafka consumer
    - Socket listener
    - Simulator
    """
    logger.info("🚀 Device stream background task started")

    while True:
        # Placeholder – non-blocking
        await asyncio.sleep(5)

