import os
from dotenv import load_dotenv
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import Response
from fastapi.responses import RedirectResponse, JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
#import fileresponse
from starlette.responses import FileResponse as fileresponse
# load .env
load_dotenv()

from app.auth import router as auth_router
from app.shipments import router as shipments_router
from app.device_stream import router as device_router
from app import db

# logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s - %(message)s")
logger = logging.getLogger("scmxpertlite")

app = FastAPI(title="SCMXpertLite API")

#app.mount(
 #   "/", 
#    StaticFiles(directory="../frontend", html=True),
#    name="frontend"
#)

# CORS
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

# minimal request logging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    client_host = getattr(request.client, "host", "unknown")
    logger.info(f"Incoming request: {request.method} {request.url} from {client_host}")
    response: Response = await call_next(request)
    logger.info(f"Response: status_code={response.status_code} for {request.method} {request.url}")
    return response

@app.get("/", response_class=JSONResponse)
async def root():
    return fileresponse("../frontend/login.html")
# debug DB connectivity endpoint
@app.get("/debug/db")
async def debug_db():
    try:
        await db.client.admin.command("ping")
        return {"db": "ok"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"DB ping failed: {exc}")

# include routers
app.include_router(auth_router, prefix="/api")
app.include_router(shipments_router, prefix="/api")
app.include_router(device_router, prefix="/api")


app.mount(
    "/", 
    StaticFiles(directory="../frontend", html=True),
    name="frontend"
)

@app.on_event("startup")
async def startup():
    try:
        await db.connect_to_mongo()
        await db.ensure_indexes()
        logger.info("MongoDB connected and indexes ensured")
    except Exception as exc:
        logger.error(f"Startup error: {exc}")
        raise
@app.get("/health")
async def health():
    return {"status": "ok"}
