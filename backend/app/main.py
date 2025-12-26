# app/main.py
import os
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(BASE_DIR, ".env")

print("DEBUG loading env from:", ENV_PATH)
print("DEBUG env exists:", os.path.exists(ENV_PATH))

load_dotenv(ENV_PATH, override=True)

print("DEBUG ENV MONGO_URL =", os.getenv("MONGO_URL"))
print("DEBUG ENV DB_NAME =", os.getenv("DB_NAME"))


import logging
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.requests import Request
from starlette.responses import Response
from starlette.staticfiles import StaticFiles
from starlette.responses import FileResponse

from app import db
from app.auth import (
    router as auth_router,
    get_current_user,
    require_role,
)
from app.shipments import router as shipments_router
from app.device_stream import router as device_router

# =====================================================
# ENV + LOGGING
# =====================================================
#BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
#load_dotenv(os.path.join(BASE_DIR, ".env"), override=True)


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
# ROOT (FRONTEND LOGIN)
# =====================================================
@app.get("/", response_class=JSONResponse)
async def root():
    return FileResponse("../frontend/login.html")

# =====================================================
# DEBUG / HEALTH
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
# PROTECTED TEST ROUTES (RBAC DEMO)
# =====================================================
@app.get("/api/profile")
async def profile(user=Depends(get_current_user)):
    """
    Any authenticated user
    """
    return {
        "id": user["_id"],
        "email": user.get("email"),
        "role": user.get("role"),
    }

@app.get("/api/admin-only")
async def admin_only(user=Depends(require_role("admin"))):
    """
    Admin-only route
    """
    return {
        "message": "Welcome admin",
        "user_id": user["_id"],
        "role": user.get("role"),
    }

# =====================================================
# ROUTERS
# =====================================================
# auth router provides:
#   POST /api/auth/token
#   POST /api/auth/signup
#   GET  /api/auth/me
app.include_router(auth_router, prefix="/api")

# business routers (can also use Depends(get_current_user) inside)
app.include_router(shipments_router, prefix="/api")
app.include_router(device_router, prefix="/api")

# =====================================================
# STATIC FRONTEND
# =====================================================
app.mount(
    "/",
    StaticFiles(directory="../frontend", html=True),
    name="frontend",
)

# =====================================================
# STARTUP / SHUTDOWN
# =====================================================
@app.on_event("startup")
async def startup():
    try:
        await db.connect_to_mongo()
        await db.ensure_indexes()
        logger.info("MongoDB connected and indexes ensured")
    except Exception as exc:
        logger.error(f"Startup error: {exc}")
        raise

