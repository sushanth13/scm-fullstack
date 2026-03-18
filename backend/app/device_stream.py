import asyncio
import logging
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app import db
from app.auth import get_current_user
from app.models import DevicePublishIn, DeviceTelemetryOut

router = APIRouter(prefix="/device", tags=["device"])
logger = logging.getLogger("scmxpertlite.device")


def _require_devices_collection():
    if db.devices_coll is None:
        raise HTTPException(status_code=500, detail="Devices collection not initialized")
    return db.devices_coll


def _normalize_ts(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _serialize_device_doc(doc: dict) -> dict:
    item = dict(doc)
    item["_id"] = str(item["_id"])
    item["data"] = item.get("data") or {}

    # Flatten common telemetry fields so the existing frontend table can read them.
    for key, value in item["data"].items():
        item.setdefault(key, value)

    if item.get("published_by") is not None:
        item["published_by"] = str(item["published_by"])

    return item


async def _store_device_payload(
    payload: DevicePublishIn,
    published_by: str | None = None,
) -> dict:
    devices_coll = _require_devices_collection()
    doc = {
        "deviceId": payload.deviceId,
        "data": payload.data,
        "ts": _normalize_ts(payload.ts),
    }
    if published_by is not None:
        doc["published_by"] = published_by

    res = await devices_coll.insert_one(doc)
    doc["_id"] = res.inserted_id
    return _serialize_device_doc(doc)


@router.post("/publish", response_model=DeviceTelemetryOut, status_code=201)
async def publish(
    payload: DevicePublishIn,
    user: Annotated[dict, Depends(get_current_user)],
):
    if not payload.deviceId:
        raise HTTPException(status_code=422, detail="deviceId is required")
    return await _store_device_payload(payload, published_by=user["_id"])


@router.post("/{device_id}/publish", response_model=DeviceTelemetryOut, status_code=201)
async def publish_from_device(device_id: str, payload: DevicePublishIn):
    normalized_payload = payload.model_copy(update={"deviceId": payload.deviceId or device_id})
    return await _store_device_payload(normalized_payload)


@router.get("/stream", response_model=list[DeviceTelemetryOut])
async def get_device_stream(
    _user: Annotated[dict, Depends(get_current_user)],
    limit: int = 50,
):
    devices_coll = _require_devices_collection()
    cursor = devices_coll.find().sort("ts", -1).limit(limit)

    items = []
    async for doc in cursor:
        items.append(_serialize_device_doc(doc))

    return items


async def start_device_stream():
    logger.info("Device stream background task started")

    try:
        while True:
            await asyncio.sleep(5)
    except asyncio.CancelledError:
        logger.info("Device stream background task stopped")
        raise
