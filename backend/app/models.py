from pydantic import BaseModel, EmailStr, Field # For defining data models with type validation (used for request and response models in FastAPI endpoints)
from typing import Optional # For optional fields in data models (e.g. created_at in ShipmentOut, which may not be present in all contexts)
from datetime import datetime
from datetime import date

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str

class LoginPayload(BaseModel): # Request model for login endpoint (contains email and password fields for user authentication)
    email: EmailStr
    password: str

class TokenOut(BaseModel): # Response model for login endpoint (contains the JWT access token and token type)
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
    id: str = Field(..., alias="_id") # Response model for shipment output (extends ShipmentIn with an additional id field that maps to MongoDB's _id field, and an optional created_at field for when the shipment was created in the database)
    created_at: Optional[datetime] = None
