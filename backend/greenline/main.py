"""FastAPI app entry point.

uvicorn greenline.main:app --host 0.0.0.0 --port 8000 (from backend/).
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from greenline.api import cases as cases_api
from greenline.api import health as health_api
from greenline.api import runs as runs_api
from greenline.config import get_settings
from greenline.events.bus import get_bus
from greenline.graph.run import RunManager
from greenline.llm.client import init_llm_client
from greenline.persistence.db import init_db

_settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    db = init_db(settings.db_full_path())
    bus = get_bus()
    run_manager = RunManager(db, bus, settings)
    llm_client = init_llm_client(settings.model_url)

    app.state.settings = settings
    app.state.db = db
    app.state.bus = bus
    app.state.run_manager = run_manager
    app.state.llm_client = llm_client

    yield

    await llm_client.aclose()
    db.close()


app = FastAPI(title="Greenline", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in _settings.cors_origins.split(",")],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_api.router)
app.include_router(cases_api.router)
app.include_router(runs_api.router)
