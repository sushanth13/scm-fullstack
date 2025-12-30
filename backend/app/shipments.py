import logging
from fastapi import APIRouter, HTTPException, Depends
from typing import List
from app import db
from app.models import ShipmentIn
from app.auth import get_current_user
from bson import ObjectId
from datetime import datetime

router = APIRouter(prefix="/shipments", tags=["shipments"])
logger = logging.getLogger("scmxpertlite.shipments")


def _obj_to_id(doc):
    doc["_id"] = str(doc["_id"])
    return doc


# ============================
# CREATE SHIPMENT
# ============================
@router.post("/", status_code=201)
async def create_shipment(
    payload: ShipmentIn,
    user: dict = Depends(get_current_user)   # ✅ FIX
):
    doc = payload.dict()
    doc["created_at"] = datetime.utcnow()
    doc["created_by"] = user["_id"]          # ✅ FIX
    doc["status"] = "pending"

    res = await db.shipments_coll.insert_one(doc)
    doc["_id"] = str(res.inserted_id)
    return doc


# ============================
# LIST SHIPMENTS
# ============================
@router.get("/", response_model=List[dict])
async def list_shipments(
    user: dict = Depends(get_current_user)   # ✅ FIX
):
    cursor = db.shipments_coll.find().sort("created_at", -1)
    items = []
    async for doc in cursor:
        items.append(_obj_to_id(doc))
    return items


# ============================
# GET SINGLE SHIPMENT
# ============================
@router.get("/{id}")
async def get_shipment(
    id: str,
    user: dict = Depends(get_current_user)   # ✅ FIX
):
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=400, detail="Invalid ID")

    doc = await db.shipments_coll.find_one({"_id": ObjectId(id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Shipment not found")

    return _obj_to_id(doc)


