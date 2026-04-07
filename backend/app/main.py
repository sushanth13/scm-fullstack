import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager, suppress

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.requests import Request
from starlette.responses import HTMLResponse, Response
from starlette.staticfiles import StaticFiles

# Allow direct execution of this file by adding the backend root to sys.path.
if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import db
from app.auth import get_current_user, require_role, router as auth_router
from app.device_stream import router as device_router, start_device_stream
from app.kafka import kafka_producer
from app.shipments import router as shipments_router

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(BASE_DIR, ".env")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
load_dotenv(ENV_PATH, override=True)
FRONTEND_DIR = os.path.abspath(
    os.getenv("FRONTEND_DIR", os.path.join(os.path.dirname(BASE_DIR), "frontend"))
)
FRONTEND_PAGE_FILES = {
    "account.html",
    "admin.html",
    "create-shipment.html",
    "device-data.html",
    "shipments.html",
}

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
templates = Jinja2Templates(directory=TEMPLATES_DIR)

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
    return templates.TemplateResponse(template_name, base_context)


def serve_frontend_file(page_name: str):
    page_path = os.path.join(FRONTEND_DIR, page_name)
    if not os.path.isfile(page_path):
        raise HTTPException(status_code=404, detail="Not Found")
    return FileResponse(page_path)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/debug/db")
async def debug_db():
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


@app.get("/", include_in_schema=False)
async def root_page():
    return RedirectResponse(url="/login.html", status_code=307)


@app.get("/index.html", response_class=HTMLResponse, include_in_schema=False)
async def index_page(request: Request):
    return render_page(
        request,
        "pages/index.html",
        page_title="SCMXpert",
        redirect_target="login.html",
    )


@app.get("/login.html", response_class=HTMLResponse, include_in_schema=False)
async def login_page(request: Request):
    return render_page(
        request,
        "pages/login.html",
        page_title="Login",
    )


@app.get("/signup.html", response_class=HTMLResponse, include_in_schema=False)
async def signup_page(request: Request):
    return render_page(
        request,
        "pages/signup.html",
        page_title="Sign Up",
    )


@app.get("/dashboard.html", response_class=HTMLResponse, include_in_schema=False)
async def dashboard_page(request: Request):
    return render_page(
        request,
        "pages/dashboard.html",
        page_title="Dashboard",
        active_nav="dashboard",
    )


@app.get("/{page_name}", include_in_schema=False)
async def frontend_page(page_name: str):
    if page_name not in FRONTEND_PAGE_FILES:
        raise HTTPException(status_code=404, detail="Not Found")
    return serve_frontend_file(page_name)


app.include_router(auth_router, prefix="/api")
app.include_router(
    shipments_router,
    prefix="/api",
    dependencies=[Depends(get_current_user)],
)
app.include_router(device_router, prefix="/api")

if os.path.isdir(FRONTEND_DIR):
    logger.info(f"Frontend found at: {FRONTEND_DIR}")

    # Serve frontend assets for both template-based pages and raw HTML pages.
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
    app.mount("/css", StaticFiles(directory=os.path.join(FRONTEND_DIR, "css")), name="css")
    app.mount("/js", StaticFiles(directory=os.path.join(FRONTEND_DIR, "js")), name="js")

else:
    logger.warning(f"Frontend directory not found at {FRONTEND_DIR}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
