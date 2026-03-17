# app/main.py

import os
import sys # For modifying sys.path to allow direct execution of this file without "python -m app.main"
import asyncio # For background tasks
import logging # For logging setup
from dotenv import load_dotenv # For .env loading

# Allow direct execution of this file by adding the backend root to sys.path.
if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException, Depends # For auth dependencies and HTTP exceptions
from fastapi.middleware.cors import CORSMiddleware  # For CORS handling (allowing frontend to access API)
from starlette.requests import Request # For type hinting in middleware
from starlette.responses import Response 
from starlette.staticfiles import StaticFiles # For serving frontend build

from app import db
from app.auth import (
    router as auth_router, # For authentication routes (e.g. /api/auth/token for login, /api/auth/signup for registration, etc.)
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
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # Get parent directory of current file (backend/app) → backend
ENV_PATH = os.path.join(BASE_DIR, ".env") # Load .env from backend root (not app/) for better separation of config and code
FRONTEND_DIR = os.path.join(os.path.dirname(BASE_DIR), "frontend") # Assuming frontend is sibling to backend
load_dotenv(ENV_PATH, override=True) # Load .env variables into environment (override=True allows .env to overwrite existing env vars, useful for local development)

# =====================================================
# LOGGING
# =====================================================
logging.basicConfig(
    level=logging.INFO, # Set default logging level to INFO for better visibility of important events (can be overridden by environment variable LOG_LEVEL)
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s", # Include logger name in format for better traceability
)
logger = logging.getLogger("scmxpertlite") # Base logger for the app (other modules can create child loggers with logging.getLogger("scmxpertlite.module_name"))

# =====================================================
# APP INIT
# =====================================================
app = FastAPI(title="SCMXpertLite API") # Set API title for better documentation and logging context

# =====================================================
# CORS
# =====================================================
allow_origins = [os.getenv("CORS_ORIGIN", "http://localhost:3000")] # Default to localhost:3000 for React frontend, can be overridden by CORS_ORIGIN env var (comma-separated for multiple origins)
if os.getenv("DEV_ALLOW_ALL_ORIGINS", "true").lower() in ("1", "true", "yes"): # Allow all origins in development for easier testing (set DEV_ALLOW_ALL_ORIGINS=false in production to disable)
    allow_origins = ["*"] # WARNING: Allowing all origins is not recommended in production environments due to security risks. Always specify allowed origins in production.

app.add_middleware(
    CORSMiddleware, # Add CORS middleware to handle cross-origin requests from the frontend
    allow_origins=allow_origins, # Use configured allowed origins   
    allow_credentials=True, # Allow cookies and authentication headers to be sent in cross-origin requests (required for JWT auth)
    allow_methods=["*"], # Allow all HTTP methods (GET, POST, etc.) in CORS preflight requests
    allow_headers=["*"], # Allow all headers in CORS preflight requests (can be restricted in production for better security)
)

# =====================================================
# REQUEST LOGGING
# =====================================================
@app.middleware("http") # Middleware to log incoming requests and responses (can be extended to log more details like headers, body, etc.)
async def log_requests(request: Request, call_next): # Log basic request info (method, URL, client IP) and response status code
    client_host = getattr(request.client, "host", "unknown") # Get client IP address from request (fallback to "unknown" if not available, e.g. in some testing environments)
    logger.info(f"{request.method} {request.url} from {client_host}") # Log incoming request method, URL, and client IP address for better traceability of API usage
    response: Response = await call_next(request) # Call the next middleware or route handler and wait for the response
    logger.info(f"Completed {response.status_code}") # Log response status code for better visibility of API outcomes (can be extended to log more details like response time, etc.)
    return response

# =====================================================
# HEALTH / DEBUG
# =====================================================
@app.get("/health") # Simple health check endpoint to verify that the API is running (can be extended to include more checks like database connectivity, etc.)
async def health():
    return {"status": "ok"}

@app.get("/debug/db") # Debug endpoint to check database connectivity (not recommended for production, can be protected with auth or removed in production)
async def debug_db():
    try:
        await db.client.admin.command("ping")
        return {"db": "ok"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"DB ping failed: {exc}")

# =====================================================
# PROTECTED ROUTES
# =====================================================
@app.get("/api/profile") # Example protected route to get current user profile (used by frontend to verify login status and get user info)
async def profile(user=Depends(get_current_user)): # Get current logged-in user profile (requires valid JWT token in Authorization header, e.g. "Authorization
    return {
        "id": user["_id"],
        "email": user.get("email"),
        "role": user.get("role"),
    }

@app.get("/api/admin-only") # Example admin-only route to demonstrate role-based access control (can be used for admin dashboard features, etc.)
async def admin_only(user=Depends(require_role("admin"))): # Require user to have "admin" role to access this route (returns 403 Forbidden if user does not have required role)
    return {
        "message": "Welcome admin",
        "user_id": user["_id"],
        "role": user.get("role"),
    }

# =====================================================
# ROUTERS
# =====================================================
app.include_router(auth_router, prefix="/api") # Include authentication routes (e.g. /api/token for login, /api/me for current user profile, etc.) without requiring auth (since these routes are for obtaining auth tokens and verifying login status)

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
    StaticFiles(directory=FRONTEND_DIR, html=True),
    name="frontend",
)

# =====================================================
# STARTUP / SHUTDOWN (PROFESSOR FORMAT)
# =====================================================
@app.on_event("startup") # Startup event to connect to MongoDB and start background tasks (e.g. device stream)
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

@app.on_event("shutdown") # Shutdown event to close MongoDB connection gracefully (important for clean resource management and preventing potential issues with open connections)
async def shutdown_event():
    await db.close_mongo()
    print("MongoDB connection closed")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)


