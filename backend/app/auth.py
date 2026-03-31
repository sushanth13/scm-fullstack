# app/auth.py
import logging
from datetime import datetime, timedelta, timezone 
from typing import Annotated 

from fastapi import APIRouter, HTTPException, Depends, status 
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm 
from jose import jwt, JWTError 
from passlib.context import CryptContext 
from pydantic import BaseModel 
from bson import ObjectId 

from app.config import settings 
from app import db 
from app.models import UserCreate 


# Router & Logger

router = APIRouter(prefix="/auth", tags=["auth"]) 

logger = logging.getLogger("scmxpertlite.auth") 
if not logger.handlers: 
    logging.basicConfig(level=logging.INFO)

ADMIN_EMAILS = set(settings.ADMIN_EMAILS.strip("{}").replace("'", "").split(",")) if settings.ADMIN_EMAILS else set()


# Security Config

JWT_SECRET = settings.JWT_SECRET 
ALGORITHM = settings.JWT_ALGORITHM 
ACCESS_TOKEN_EXPIRE_SECONDS = settings.JWT_EXP_SECONDS 

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto") 

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token") 


# Models

class TokenOut(BaseModel): 
    access_token: str
    token_type: str = "bearer" 


class UserProfile(BaseModel):
    _id: str
    name: str
    email: str
    role: str


def resolve_user_role(email: str, existing_role: str | None = None) -> str:
    if email.strip().lower() in ADMIN_EMAILS:
        return "admin"
    return existing_role or "user"



# Password Helpers

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)



# JWT Helpers

def create_access_token(
    subject: str,
    role: str,
    expires_delta: timedelta | None = None,
) -> str: 
    expire = datetime.now(timezone.utc) + (
        expires_delta
        if expires_delta
        else timedelta(seconds=ACCESS_TOKEN_EXPIRE_SECONDS)
    )

    payload = {
        "sub": subject,
        "role": role,
        "exp": expire,
    }

    return jwt.encode(payload, JWT_SECRET, algorithm=ALGORITHM)



# Dependencies

async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)] 
) -> dict: 
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM]) 
        user_id = payload.get("sub")
        role = payload.get("role")

        if not user_id or not role:
            raise credentials_exception

    except JWTError:
        raise credentials_exception

    if db.users_coll is None:
        raise HTTPException(status_code=500, detail="Database not initialized")

    user = await db.users_coll.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise credentials_exception

    user["_id"] = str(user["_id"])
    user["role"] = resolve_user_role(user.get("email", ""), role)
    return user


def require_role(required_role: str):
    async def role_checker(
        user: Annotated[dict, Depends(get_current_user)]
    ):
        if user.get("role") != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return user

    return role_checker



# Current User Endpoint

@router.get(
    "/me",
    response_model=UserProfile,
    summary="Get current logged-in user",
)
async def read_current_user(
    user: Annotated[dict, Depends(get_current_user)]
):
    """
    Used by frontend to verify login status.
    """
    return {
        "_id": user["_id"],
        "name": user.get("name", ""),
        "email": user.get("email", ""),
        "role": user.get("role", "user"),
    }




# Login Endpoint

@router.post(
    "/token",
    response_model=TokenOut,
    summary="Login and get access token",
)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
):
    if db.users_coll is None:
        raise HTTPException(
            status_code=500,
            detail="Database not initialized",
        )

    #  Login uses email as username
    user = await db.users_coll.find_one({"email": form_data.username})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not verify_password(form_data.password, user.get("password", "")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    resolved_role = resolve_user_role(user.get("email", ""), user.get("role"))

    await db.users_coll.update_one(
        {"_id": user["_id"]},
        {
            "$set": {
                "role": resolved_role,
                "last_login_at": datetime.now(timezone.utc),
            }
        },
    )

    access_token = create_access_token(
        subject=str(user["_id"]),
        role=resolved_role,
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }



# Signup Endpoint

@router.post(
    "/signup",
    status_code=201,
    summary="Create new user account",
)
async def signup(user: UserCreate):
    if db.users_coll is None:
        raise HTTPException(
            status_code=500,
            detail="Database not initialized",
        )

    existing = await db.users_coll.find_one({"email": user.email})
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Email already registered",
        )

    hashed_password = get_password_hash(user.password)

    doc = {
        "name": user.name,
        "email": user.email,
        "password": hashed_password,
        "role": resolve_user_role(user.email),
        "created_at": datetime.now(timezone.utc),
    }

    result = await db.users_coll.insert_one(doc)

    return {
        "message": "User created successfully",
        "user_id": str(result.inserted_id),
    }


@router.post("/logout", summary="Record logout activity")
async def logout(
    user: Annotated[dict, Depends(get_current_user)],
):
    if db.users_coll is None:
        raise HTTPException(status_code=500, detail="Database not initialized")

    await db.users_coll.update_one(
        {"_id": ObjectId(user["_id"])},
        {"$set": {"last_logout_at": datetime.now(timezone.utc)}},
    )

    return {"message": "Logout recorded"}


@router.get("/admin/overview", summary="Admin overview")
async def admin_overview(
    user: Annotated[dict, Depends(require_role("admin"))],
):
    if db.users_coll is None or db.shipments_coll is None or db.devices_coll is None:
        raise HTTPException(status_code=500, detail="Database not initialized")

    users = []
    async for doc in db.users_coll.find().sort("created_at", -1):
        users.append(
            {
                "id": str(doc["_id"]),
                "name": doc.get("name", ""),
                "email": doc.get("email", ""),
                "role": resolve_user_role(doc.get("email", ""), doc.get("role")),
                "created_at": doc.get("created_at"),
                "last_login_at": doc.get("last_login_at"),
                "last_logout_at": doc.get("last_logout_at"),
            }
        )

    shipments = []
    async for doc in db.shipments_coll.find().sort("created_at", -1).limit(20):
        shipments.append(
            {
                "id": str(doc["_id"]),
                "shipmentNumber": doc.get("shipmentNumber"),
                "deviceId": doc.get("deviceId"),
                "goodsType": doc.get("goodsType"),
                "status": doc.get("status", "pending"),
                "created_at": doc.get("created_at"),
            }
        )

    devices = []
    async for doc in db.devices_coll.find().sort("ts", -1).limit(20):
        payload = dict(doc.get("data") or {})
        if not payload:
            payload = {
                key: value
                for key, value in doc.items()
                if key not in {"_id", "deviceId", "ts", "published_by"}
            }

        devices.append(
            {
                "id": str(doc["_id"]),
                "deviceId": doc.get("deviceId") or str(doc.get("Device_ID", "")),
                "ts": doc.get("ts") or doc.get("Timestamp"),
                "battery": payload.get("Battery_Level"),
                "temperature": payload.get("First_Sensor_temperature"),
                "humidity": payload.get("Humidity"),
                "routeFrom": payload.get("Route_From"),
                "routeTo": payload.get("Route_To"),
                "published_by": str(doc.get("published_by")) if doc.get("published_by") else None,
            }
        )

    return {
        "viewer": {
            "id": user["_id"],
            "email": user.get("email"),
            "role": user.get("role"),
        },
        "summary": {
            "user_count": len(users),
            "admin_count": sum(1 for item in users if item["role"] == "admin"),
            "shipment_count": await db.shipments_coll.count_documents({}),
            "device_event_count": await db.devices_coll.count_documents({}),
        },
        "users": users,
        "shipments": shipments,
        "devices": devices,
    }


