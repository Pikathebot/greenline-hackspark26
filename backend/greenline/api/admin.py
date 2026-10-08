"""POST /api/admin/reset-memory (docs/05-BACKEND-SPEC.md §1). Clears
memory traces, used to show a cold #0142 on stage."""

from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter()


@router.post("/api/admin/reset-memory")
async def reset_memory(request: Request) -> dict:
    memory_store = request.app.state.memory_store
    memory_store.reset()
    return {"reset": True}
