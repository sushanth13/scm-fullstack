import asyncio
import logging
from datetime import datetime, timezone
from typing import Annotated, Any

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


def _normalize_ts(value: Any) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    if isinstance(value, (int, float)):
        # Treat 13-digit values as milliseconds and 10-digit values as seconds.
        timestamp = float(value)
        if timestamp > 1_000_000_000_000:
            timestamp = timestamp / 1000.0
        return datetime.fromtimestamp(timestamp, tz=timezone.utc)
    if isinstance(value, str):
        try:
            raw = value.strip()
            if raw.replace(".", "", 1).isdigit():
                timestamp = float(raw)
                if timestamp > 1_000_000_000_000:
                    timestamp = timestamp / 1000.0
                return datetime.fromtimestamp(timestamp, tz=timezone.utc)

            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=timezone.utc)
            return parsed
        except ValueError:
            return datetime.now(timezone.utc)
    return datetime.now(timezone.utc)


def _extract_legacy_data(item: dict) -> dict:
    ignored_keys = {
        "_id",
        "deviceId",
        "Device_ID",
        "ts",
        "Timestamp",
        "published_by",
        "kafka_offset",
        "kafka_partition",
        "ingested_at",
    }
    return {
        key: value
        for key, value in item.items()
        if key not in ignored_keys
    }


def _serialize_device_doc(doc: dict) -> dict:
    item = dict(doc)
    doc_id = item.get("_id")
    item["_id"] = str(doc_id)

    data = item.get("data") or _extract_legacy_data(item)
    item["data"] = data

    if not item.get("deviceId"):
        legacy_id = item.get("Device_ID")
        item["deviceId"] = str(legacy_id) if legacy_id is not None else "unknown-device"

    raw_ts = item.get("ts") or item.get("Timestamp")
    if raw_ts is None and hasattr(doc_id, "generation_time"):
        raw_ts = doc_id.generation_time
    item["ts"] = _normalize_ts(raw_ts)

    for key, value in data.items():
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


@router.get("/stream")
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
