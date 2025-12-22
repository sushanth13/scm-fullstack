from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime

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
    name: str
    deviceId: str
    origin: Optional[str] = None
    destination: Optional[str] = None

class ShipmentOut(ShipmentIn):
    id: str = Field(..., alias="_id")
    created_at: Optional[datetime] = None
