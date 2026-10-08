"""POST /api/admin/reset-memory, POST /api/admin/export-demo-runs
(docs/05-BACKEND-SPEC.md §1)."""

from __future__ import annotations

from fastapi import APIRouter, Request

from greenline.demo.export import export_all

router = APIRouter()


@router.post("/api/admin/reset-memory")
async def reset_memory(request: Request) -> dict:
    memory_store = request.app.state.memory_store
    memory_store.reset()
    return {"reset": True}


@router.post("/api/admin/export-demo-runs")
async def export_demo_runs(request: Request) -> dict:
    db = request.app.state.db
    settings = request.app.state.settings
    return export_all(db, settings.demo_runs_path())
