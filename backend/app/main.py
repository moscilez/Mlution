from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from redis import Redis
from rq import Worker
import logging


from . import db
from .api.projects import router as projects_router
from .api.auth import router as auth_router
from .api.competition import router as competition_router
from .settings import get_settings
from .middleware import ApiMiddleware
from .config import DEMO_CSV, ensure_dirs
from .demo_data import generate_demo_csv

logging.basicConfig(level=logging.INFO, format="%(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_dirs()
    db.init_db()
    if not DEMO_CSV.exists():
        generate_demo_csv(DEMO_CSV)
    yield
    db.engine.dispose()


app = FastAPI(title="Mlution API", version="0.1.0", lifespan=lifespan)

app.add_middleware(ApiMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects_router, prefix="/api")
app.include_router(auth_router, prefix="/api")
app.include_router(competition_router, prefix="/api")


@app.get("/api/health")
def health():
    try:
        db.init_db()
        result = {"status": "ok", "database": "ok", "redis": "disabled", "worker": "inline"}
        if get_settings().job_mode == "redis":
            connection = Redis.from_url(get_settings().redis_url, socket_connect_timeout=2, socket_timeout=2)
            connection.ping()
            result["redis"] = "ok"
            result["worker"] = "ok" if Worker.all(connection=connection, queue=None) else "unavailable"
            if result["worker"] != "ok":
                return JSONResponse(result, status_code=503)
        return result
    except Exception:
        return JSONResponse({"status": "unavailable"}, status_code=503)


@app.exception_handler(Exception)
async def unexpected_error(request, exc):
    logging.exception("Unhandled API error", exc_info=exc)
    return JSONResponse({"detail": "Unexpected server error. Please retry."}, status_code=500)
