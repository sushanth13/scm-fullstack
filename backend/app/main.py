# app/main.py
# app/main.py
import os
import asyncio
import logging
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.staticfiles import StaticFiles

from app import db
from app.auth import (
    router as auth_router,
    get_current_user,
    require_role,
)
from app.shipments import router as shipments_router
from app.device_stream import (
    router as device_router,
    start_device_stream,   
)

# =====================================================
# ENV
# =====================================================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(BASE_DIR, ".env")
load_dotenv(ENV_PATH, override=True)

# =====================================================
# LOGGING
# =====================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("scmxpertlite")

# =====================================================
# APP INIT
# =====================================================
app = FastAPI(title="SCMXpertLite API")

# =====================================================
# CORS
# =====================================================
allow_origins = [os.getenv("CORS_ORIGIN", "http://localhost:3000")]
if os.getenv("DEV_ALLOW_ALL_ORIGINS", "true").lower() in ("1", "true", "yes"):
    allow_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =====================================================
# REQUEST LOGGING
# =====================================================
@app.middleware("http")
async def log_requests(request: Request, call_next):
    client_host = getattr(request.client, "host", "unknown")
    logger.info(f"{request.method} {request.url} from {client_host}")
    response: Response = await call_next(request)
    logger.info(f"Completed {response.status_code}")
    return response

# =====================================================
# HEALTH / DEBUG
# =====================================================
@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/debug/db")
async def debug_db():
    try:
        await db.client.admin.command("ping")
        return {"db": "ok"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"DB ping failed: {exc}")

# =====================================================
# PROTECTED ROUTES
# =====================================================
@app.get("/api/profile")
async def profile(user=Depends(get_current_user)):
    return {
        "id": user["_id"],
        "email": user.get("email"),
        "role": user.get("role"),
    }

@app.get("/api/admin-only")
async def admin_only(user=Depends(require_role("admin"))):
    return {
        "message": "Welcome admin",
        "user_id": user["_id"],
        "role": user.get("role"),
    }

# =====================================================
# ROUTERS
# =====================================================
app.include_router(auth_router, prefix="/api")

app.include_router(
    shipments_router,
    prefix="/api",
    dependencies=[Depends(get_current_user)]
)

app.include_router(
    device_router,
    prefix="/api",
    dependencies=[Depends(get_current_user)]
)

# =====================================================
# STATIC FRONTEND
# =====================================================
app.mount(
    "/",
    StaticFiles(directory="../frontend", html=True),
    name="frontend",
)

# =====================================================
# STARTUP / SHUTDOWN (PROFESSOR FORMAT)
# =====================================================
@app.on_event("startup")
async def startup_event():
    try:
        # MongoDB
        await db.connect_to_mongo()
        await db.ensure_indexes()
        print("MongoDB connected and indexes ensured")

        # 🔥 Device stream background task (MANDATORY)
        asyncio.create_task(start_device_stream())
        print("Device stream started")

    except Exception as exc:
        print("Startup failed:", exc)
        raise

@app.on_event("shutdown")
async def shutdown_event():
    await db.close_mongo()
    print("MongoDB connection closed")
 


