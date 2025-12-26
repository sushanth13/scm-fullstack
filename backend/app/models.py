from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from datetime import date

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str

class LoginPayload(BaseModel):
    email: EmailStr
    password: str

class TokenOut(BaseModel):
    access_token: str

class ShipmentIn(BaseModel):
    shipmentNumber: str
    containerNumber: str
    routeDetails: str
    goodsType: str
    deviceId: str
    expectedDeliveryDate: date
    poNumber: str
    deliveryNumber: str
    ndcNumber: str
    batchId: str
    serialNumber: str
    description: str

class ShipmentOut(ShipmentIn):
    id: str = Field(..., alias="_id")
    created_at: Optional[datetime] = None
