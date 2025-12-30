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

# =====================================================
# Router & Logger
# =====================================================
router = APIRouter(prefix="/auth", tags=["auth"])

logger = logging.getLogger("scmxpertlite.auth")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)

# =====================================================
# Security Config
# =====================================================
JWT_SECRET = settings.JWT_SECRET
ALGORITHM = settings.JWT_ALGORITHM
ACCESS_TOKEN_EXPIRE_SECONDS = settings.JWT_EXP_SECONDS

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")

# =====================================================
# Models
# =====================================================
class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserProfile(BaseModel):
    _id: str
    name: str
    email: str
    role: str


# =====================================================
# Password Helpers
# =====================================================
def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


# =====================================================
# JWT Helpers
# =====================================================
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


# =====================================================
# Dependencies
# =====================================================
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
    user["role"] = role
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


# =====================================================
# Current User Endpoint (IMPORTANT)
# =====================================================
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



# =====================================================
# Login Endpoint
# =====================================================
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

    # 🔹 Login uses EMAIL as username
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

    access_token = create_access_token(
        subject=str(user["_id"]),
        role=user.get("role", "user"),
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


# =====================================================
# Signup Endpoint
# =====================================================
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
        "role": "user",
        "created_at": datetime.now(timezone.utc),
    }

    result = await db.users_coll.insert_one(doc)

    return {
        "message": "User created successfully",
        "user_id": str(result.inserted_id),
    }


