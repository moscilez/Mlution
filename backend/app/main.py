from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import db
from .api.projects import router as projects_router
from .config import DEMO_CSV, ensure_dirs
from .demo_data import generate_demo_csv


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_dirs()
    db.init_db()
    if not DEMO_CSV.exists():
        generate_demo_csv(DEMO_CSV)
    yield


app = FastAPI(title="Mlution API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects_router, prefix="/api")
