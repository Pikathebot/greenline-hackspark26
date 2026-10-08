"""FastAPI app entry point.

uvicorn greenline.main:app --host 0.0.0.0 --port 8000 (from backend/).
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from greenline.api import admin as admin_api
from greenline.api import cases as cases_api
from greenline.api import health as health_api
from greenline.api import runs as runs_api
from greenline.api import scoreboard as scoreboard_api
from greenline.config import get_settings
from greenline.events.bus import get_bus
from greenline.graph.run import RunManager
from greenline.llm.client import init_llm_client
from greenline.memory.embed import init_embed_client
from greenline.memory.store import init_memory_store
from greenline.persistence.db import init_db

_settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    db = init_db(settings.db_full_path())
    bus = get_bus()
    github_client = None
    watcher_task = None
    if settings.github_enabled():
        from greenline.github.client import GitHubClient

        github_client = GitHubClient(settings.github_repo, settings.github_token)
    run_manager = RunManager(db, bus, settings, github_client=github_client)
    if github_client is not None:
        from greenline.github.watch import GitHubWatcher

        watcher_task = asyncio.create_task(
            GitHubWatcher(settings, run_manager, github_client).run()
        )
    llm_client = init_llm_client(settings.model_url)
    embed_client = init_embed_client(settings.embed_url)
    memory_store = init_memory_store(db.connection)

    app.state.settings = settings
    app.state.db = db
    app.state.bus = bus
    app.state.run_manager = run_manager
    app.state.llm_client = llm_client
    app.state.embed_client = embed_client
    app.state.memory_store = memory_store

    yield

    if watcher_task is not None:
        watcher_task.cancel()
    if github_client is not None:
        github_client.close()
    await llm_client.aclose()
    await embed_client.aclose()
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
app.include_router(admin_api.router)
app.include_router(scoreboard_api.router)
