from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app import db
from app.auth import get_current_user
from datetime import datetime

router = APIRouter(prefix="/device", tags=["device"])

class DevicePayload(BaseModel):
    deviceId: str
    data: dict

@router.post("/publish")
async def publish(payload: DevicePayload, user_id: str = Depends(get_current_user)):
    doc = {
        "deviceId": payload.deviceId,
        "data": payload.data,
        "ts": datetime.utcnow(),
        "published_by": user_id
    }
    res = await db.devices_coll.insert_one(doc)
    return {"_id": str(res.inserted_id)}
