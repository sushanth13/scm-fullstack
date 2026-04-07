from datetime import date, datetime
from typing import Any
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


class ApiModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class UserCreate(ApiModel):
    name: str
    email: EmailStr
    password: str


class LoginPayload(ApiModel):
    email: EmailStr
    password: str


class UserRoleUpdate(ApiModel):
    role: Literal["admin", "user"]


class TokenOut(ApiModel):
    access_token: str
    token_type: str = "bearer"


class ShipmentIn(ApiModel):
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
    created_at: datetime | None = None
    status: str = "pending"


class DevicePublishIn(ApiModel):
    deviceId: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
    ts: datetime | None = None

    @model_validator(mode="before")
    @classmethod
    def normalize_payload(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value

        if "data" in value:
            payload = dict(value)
            payload.setdefault("ts", value.get("ts"))
            return payload

        device_id = value.get("deviceId")
        ts = value.get("ts")
        data = {
            key: item
            for key, item in value.items()
            if key not in {"deviceId", "ts"}
        }
        return {
            "deviceId": device_id,
            "ts": ts,
            "data": data,
        }


class DeviceTelemetryOut(ApiModel):
    model_config = ConfigDict(populate_by_name=True, extra="allow")

    id: str = Field(..., alias="_id")
    deviceId: str
    ts: datetime
    data: dict[str, Any] = Field(default_factory=dict)
    Device_ID: str | int | None = None
    Battery_Level: float | int | None = None
    First_Sensor_temperature: float | int | None = None
    Humidity: float | int | None = None
    Route_From: str | None = None
    Route_To: str | None = None
    Timestamp: datetime | str | int | float | None = None
    published_by: str | None = None
