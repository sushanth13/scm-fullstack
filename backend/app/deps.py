import os
from fastapi import Header, HTTPException
from jose import jwt, JWTError

SECRET = os.getenv("JWT_SECRET", "changeme_supersecret_key")
ALGO = os.getenv("JWT_ALGORITHM", "HS256")

async def get_current_user(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid auth scheme")

    try:
        payload = jwt.decode(token, SECRET, algorithms=[ALGO])
        return payload.get("sub")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
