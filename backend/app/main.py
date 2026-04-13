import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager, suppress

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from starlette.requests import Request
from starlette.responses import HTMLResponse, Response
from starlette.staticfiles import StaticFiles

# Allow direct execution of this file by adding the backend root to sys.path.
if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) 

from app import db
from app.auth import get_current_user, require_role, router as auth_router
from app.config import settings
from app.device_stream import router as device_router, start_device_stream
from app.kafka import kafka_producer
from app.shipments import router as shipments_router

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(BASE_DIR, ".env")
load_dotenv(ENV_PATH, override=True)


def _is_frontend_dir(path: str) -> bool:
    return os.path.isfile(os.path.join(path, "index.html"))


def _resolve_frontend_dir() -> str:
    configured_frontend_dir = os.getenv("FRONTEND_DIR")
    candidate_dirs = [
        configured_frontend_dir,
        os.path.join(BASE_DIR, "frontend"),
        os.path.join(os.path.dirname(BASE_DIR), "frontend"),
    ]
    normalized_candidates = [
        os.path.abspath(path) for path in candidate_dirs if path
    ]

    for candidate in normalized_candidates:
        if _is_frontend_dir(candidate):
            return candidate

    for candidate in normalized_candidates:
        if os.path.isdir(candidate):
            return candidate

    return os.path.abspath(os.path.join(BASE_DIR, "frontend"))


def _build_cors_origins() -> list[str]:
    if settings.DEV_ALLOW_ALL_ORIGINS:
        return ["*"]
    if settings.CORS_ORIGIN:
        return [settings.CORS_ORIGIN]
    return ["http://localhost:3000"]


FRONTEND_DIR = _resolve_frontend_dir()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("scmxpertlite")


@asynccontextmanager
async def lifespan(app: FastAPI):
    device_stream_task = None
    try:
        await db.connect_to_mongo()
        await db.ensure_indexes()
        await kafka_producer.start()

        device_stream_task = asyncio.create_task(start_device_stream())
        app.state.device_stream_task = device_stream_task
        logger.info("Application startup completed")
        
        yield
    finally:
        if device_stream_task is not None:
            device_stream_task.cancel()
            with suppress(asyncio.CancelledError):
                await device_stream_task

        await kafka_producer.stop()
        await db.close_mongo()
        logger.info("Application shutdown completed")
    


app = FastAPI(title="SCMXpertLite API", lifespan=lifespan)
# Jinja renders the HTML files from the actual frontend folder in this project.
templates = Jinja2Templates(directory=FRONTEND_DIR)

allow_origins = _build_cors_origins()

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    client_host = getattr(request.client, "host", "unknown")
    logger.info("%s %s from %s", request.method, request.url, client_host)
    response: Response = await call_next(request)
    logger.info("Completed %s", response.status_code)
    return response


def render_page(request: Request, template_name: str, **context):
    base_context = {
        "request": request,
        "app_name": "SCMXpert",
    }
    base_context.update(context)
    return templates.TemplateResponse(
        request=request,
        name=template_name,
        context=base_context,
    )


def frontend_template_exists(template_name: str) -> bool:
    template_path = os.path.abspath(os.path.join(FRONTEND_DIR, template_name))
    try:
        return (
            os.path.commonpath([FRONTEND_DIR, template_path]) == FRONTEND_DIR
            and os.path.isfile(template_path)           
        )
    except ValueError:
        return False


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/debug/db", include_in_schema=False)
async def debug_db(_user=Depends(require_role("admin"))):
    if db.client is None:
        raise HTTPException(status_code=500, detail="Database client not initialized")
    try:
        await db.client.admin.command("ping")
        return {"db": "ok"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"DB ping failed: {exc}") from exc


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


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
@app.get("/index.html", response_class=HTMLResponse, include_in_schema=False)
async def index_page(request: Request):
    return render_page(
        request,
        "index.html",
        page_title="SCMXpert",
        redirect_target="login.html",
    )


@app.get("/login.html", response_class=HTMLResponse, include_in_schema=False)
async def login_page(request: Request):
    return render_page(
        request,
        "login.html",
        page_title="Login - SCMXpert",
    )


@app.get("/signup.html", response_class=HTMLResponse, include_in_schema=False)
async def signup_page(request: Request):
    return render_page(
        request,
        "signup.html",
        page_title="Signup - SCMXpert",
    )


@app.get("/dashboard.html", response_class=HTMLResponse, include_in_schema=False)
async def dashboard_page(request: Request):
    return render_page(
        request,
        "dashboard.html",
        page_title="Dashboard - SCMXpert",
        active_nav="dashboard",
    )


@app.get("/{page_name}.html", response_class=HTMLResponse, include_in_schema=False)
async def frontend_page(request: Request, page_name: str):
    template_name = f"{page_name}.html"
    if not frontend_template_exists(template_name):
        raise HTTPException(status_code=404, detail="Page not found")
    return render_page(request, template_name)


app.include_router(auth_router, prefix="/api")
app.include_router(
    shipments_router,
    prefix="/api",
    dependencies=[Depends(get_current_user)],
)
app.include_router(device_router, prefix="/api")

if os.path.isdir(FRONTEND_DIR):
    logger.info("Frontend found at: %s", FRONTEND_DIR)

    for asset_dir in ("css", "js"):
        asset_path = os.path.join(FRONTEND_DIR, asset_dir)
        if os.path.isdir(asset_path):
            app.mount(f"/{asset_dir}", StaticFiles(directory=asset_path), name=asset_dir)
else:
    logger.warning("Frontend directory not found at %s", FRONTEND_DIR)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=True,
    )
