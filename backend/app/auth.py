import os
import logging
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends
from passlib.context import CryptContext
from jose import jwt
from app import db
from app.models import UserCreate, TokenOut, LoginPayload
from app.deps import get_current_user
from pydantic import BaseModel
from pymongo.errors import DuplicateKeyError
from bson import ObjectId

router = APIRouter(prefix="/auth", tags=["auth"])

# logger
logger = logging.getLogger("scmxpertlite.auth")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)

# use bcrypt with auto-deprecation fallback
pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

SECRET = os.getenv("JWT_SECRET", "changeme_supersecret_key")
ALGO = os.getenv("JWT_ALGORITHM", "HS256")
EXP = int(os.getenv("JWT_EXP_SECONDS", "604800"))

class LoginPayload(BaseModel):
    email: str
    password: str

class UserProfile(BaseModel):
    _id: str
    name: str
    email: str

@router.get("/me", response_model=UserProfile)
async def get_user_profile(user_id: str = Depends(get_current_user)):
    if db.users_coll is None:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    try:
        user = await db.users_coll.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {
            "_id": str(user["_id"]),
            "name": user.get("name", "User"),
            "email": user.get("email", "")
        }
    except Exception as exc:
        logger.exception("Error fetching user profile for user_id=%s", user_id)
        raise HTTPException(status_code=500, detail="Failed to fetch user profile")

@router.post("/signup", status_code=201)
async def signup(payload: UserCreate):
    # ensure DB is initialized
    if db.users_coll is None:
        raise HTTPException(status_code=500, detail="Database not initialized")

    try:
        existing = await db.users_coll.find_one({"email": payload.email})
        if existing:
            raise HTTPException(status_code=400, detail="User already exists")

        # hash password (bcrypt_sha256 used by context)
        hashed = pwd.hash(payload.password)

        user_doc = {
            "name": payload.name,
            "email": payload.email,
            "password": hashed,
            "created_at": datetime.utcnow()
        }
        res = await db.users_coll.insert_one(user_doc)
        logger.info("User created: %s", payload.email)
        return {"_id": str(res.inserted_id)}

    except DuplicateKeyError:
        logger.warning("Duplicate key during signup for email=%s", payload.email)
        raise HTTPException(status_code=400, detail="User with this email already exists")
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Unhandled error during signup for email=%s", payload.email)
        # surface a clearer internal error for debugging
        raise HTTPException(status_code=500, detail=f"Signup failed: {str(exc)}")

@router.post("/login", response_model=TokenOut)
async def login(payload: LoginPayload):
    if db.users_coll is None:
        raise HTTPException(status_code=500, detail="Database not initialized")

    user = await db.users_coll.find_one({"email": payload.email})
    if not user:
        logger.warning("Login failed: user not found for email=%s", payload.email)
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    try:
        is_valid = pwd.verify(payload.password, user["password"])
        logger.info("Password verification for %s: %s", payload.email, is_valid)
        if not is_valid:
            raise HTTPException(status_code=401, detail="Invalid credentials")
    except Exception as e:
        logger.exception("Password verification error for email=%s: %s", payload.email, str(e))
        raise HTTPException(status_code=401, detail="Invalid credentials")

    expire = datetime.utcnow() + timedelta(seconds=EXP)
    token = jwt.encode({"sub": str(user["_id"]), "exp": expire.timestamp()}, SECRET, algorithm=ALGO)
    return {"access_token": token}
