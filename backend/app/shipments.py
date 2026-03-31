import logging
from datetime import date, datetime

from bson import ObjectId
from fastapi import APIRouter, HTTPException

from app import db
from app.models import ShipmentIn, ShipmentOut

router = APIRouter(prefix="/shipments", tags=["shipments"])
logger = logging.getLogger("scmxpertlite.shipments")


def _require_shipments_collection():
    if db.shipments_coll is None:
        raise HTTPException(status_code=500, detail="Shipments collection not initialized")
    return db.shipments_coll


def _serialize_shipment(doc: dict) -> dict: 
    item = dict(doc)
    item["_id"] = str(item["_id"])

    expected = item.get("expectedDeliveryDate")
    if isinstance(expected, datetime):
        item["expectedDeliveryDate"] = expected.date()
    elif isinstance(expected, date):
        item["expectedDeliveryDate"] = expected

    return item


@router.post("/", status_code=201, response_model=ShipmentOut)
async def create_shipment(payload: ShipmentIn):
    shipments_coll = _require_shipments_collection()

    doc = payload.model_dump()
    doc["expectedDeliveryDate"] = datetime.combine(payload.expectedDeliveryDate, datetime.min.time())
    doc["created_at"] = datetime.utcnow()
    doc["status"] = "pending"

    res = await shipments_coll.insert_one(doc)
    doc["_id"] = res.inserted_id

    return _serialize_shipment(doc)


@router.get("/", response_model=list[ShipmentOut])
async def list_shipments():
    shipments_coll = _require_shipments_collection()
    cursor = shipments_coll.find().sort("created_at", -1)

    items = []
    async for doc in cursor:
        items.append(_serialize_shipment(doc))

    return items


@router.get("/{id}", response_model=ShipmentOut)
async def get_shipment(id: str):
    shipments_coll = _require_shipments_collection()

    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=400, detail="Invalid ID")

    doc = await shipments_coll.find_one({"_id": ObjectId(id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Shipment not found")

    return _serialize_shipment(doc)
