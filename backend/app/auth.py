# app/auth.py
import logging
from datetime import datetime, timedelta, timezone # For JWT expiration handling
from typing import Annotated # For type hinting with FastAPI dependencies

from fastapi import APIRouter, HTTPException, Depends, status # For auth dependencies and HTTP exceptions
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm #
from jose import jwt, JWTError # For JWT encoding and decoding
from passlib.context import CryptContext # For password hashing and verification
from pydantic import BaseModel # For request and response models
from bson import ObjectId # For MongoDB ObjectId handling

from app.config import settings # For accessing configuration settings (e.g. JWT secret, database URL)
from app import db
from app.models import UserCreate

# =====================================================
# Router & Logger
# =====================================================
router = APIRouter(prefix="/auth", tags=["auth"]) # Prefix all auth routes with /auth (e.g. /auth/token for login, /auth/signup for registration, etc.)

logger = logging.getLogger("scmxpertlite.auth") # Set up logger for this module (can be configured to log to file, etc. in production)
if not logger.handlers: # Avoid adding multiple handlers if this module is imported multiple times (e.g. in tests)
    logging.basicConfig(level=logging.INFO)

# =====================================================
# Security Config
# =====================================================
JWT_SECRET = settings.JWT_SECRET # Secret key for signing JWT tokens (should be a long, random string in production and kept secure, e.g. in environment variables or secret management systems)
ALGORITHM = settings.JWT_ALGORITHM #` Algorithm used for JWT encoding and decoding (e.g. HS256, RS256, etc.)`
ACCESS_TOKEN_EXPIRE_SECONDS = settings.JWT_EXP_SECONDS # Access token expiration time in seconds (e.g. 3600 for 1 hour, 86400 for 1 day, etc.)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto") # Password hashing context using bcrypt (bcrypt is a secure hashing algorithm designed for password hashing, it automatically handles salting and is resistant to brute-force attacks)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token") # OAuth2 scheme for FastAPI to extract JWT token from Authorization header (expects "Authorization: Bearer <token>" in requests, tokenUrl is the endpoint where clients can obtain JWT tokens, e.g. by providing username and password)

# =====================================================
# Models
# =====================================================
class TokenOut(BaseModel): # Response model for access token output (used in login endpoint)
    access_token: str
    token_type: str = "bearer" # Token type is typically "bearer" for JWT tokens, indicating that the token should be sent in the Authorization header as "Bearer <token>"


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
) -> str: # Create a JWT access token with the given subject (user ID), role, and expiration time (returns the encoded JWT token as a string)
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
    token: Annotated[str, Depends(oauth2_scheme)] # Extract JWT token from Authorization header using OAuth2 scheme
) -> dict: # Get current logged-in user based on JWT token (used as a dependency in protected routes to enforce authentication)
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM]) # Decode JWT token to get the payload (raises JWTError if token is invalid, expired, etc.)
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


