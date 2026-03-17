import logging # For logging in this module
from fastapi import APIRouter, HTTPException
from app import db
from app.models import ShipmentIn
from bson import ObjectId
from datetime import datetime, time

router = APIRouter(prefix="/shipments", tags=["shipments"])
logger = logging.getLogger("scmxpertlite.shipments")


def _obj_to_id(doc):
    doc["_id"] = str(doc["_id"])
    return doc


@router.post("/", status_code=201) # Create shipment
async def create_shipment(payload: ShipmentIn): 
    doc = payload.dict() # Convert Pydantic model to dict for MongoDB insertion

    # ✅ FIX: Convert date → datetime (MongoDB compatible)
    if doc.get("expectedDeliveryDate"): # Convert date to datetime at midnight
        doc["expectedDeliveryDate"] = datetime.combine(
            doc["expectedDeliveryDate"],
            time.min
        )

    doc["created_at"] = datetime.utcnow()
    doc["status"] = "pending"

    res = await db.shipments_coll.insert_one(doc)
    doc["_id"] = str(res.inserted_id)

    return doc


@router.get("/")
async def list_shipments():
    cursor = db.shipments_coll.find().sort("created_at", -1)
    items = []

    async for doc in cursor:
        items.append(_obj_to_id(doc))

    return items


@router.get("/{id}")
async def get_shipment(id: str):
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=400, detail="Invalid ID")

    doc = await db.shipments_coll.find_one({"_id": ObjectId(id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Shipment not found")

    return _obj_to_id(doc)



