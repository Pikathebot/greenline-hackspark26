"""SSE stream + /api/runs/active (docs/05-BACKEND-SPEC.md §1, §3).

Order: look up the run (404 if missing) -> subscribe to the bus first if it's
still running -> send the persisted prefix -> tail the bus, deduping by seq ->
a 15 s `: ping` on silence -> always unsubscribe in finally.
"""

from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

router = APIRouter()

PING_INTERVAL_S = 15


@router.get("/api/runs/active")
async def active_run(request: Request) -> dict | None:
    run_manager = request.app.state.run_manager
    active = run_manager.active
    if active is None:
        return None
    run_id, case_id = active
    return {"runId": run_id, "caseId": case_id}


@router.get("/api/runs/{run_id}/stream")
async def stream_run(run_id: str, request: Request) -> StreamingResponse:
    db = request.app.state.db
    bus = request.app.state.bus

    run_row = db.get_run(run_id)
    if run_row is None:
        raise HTTPException(status_code=404, detail=f"unknown run {run_id!r}")

    # Subscribe BEFORE replaying the persisted prefix, so events emitted in
    # between are never lost. A run that already finished has nothing left to
    # tail, so don't subscribe (its topic may already be closed).
    is_running = run_row["status"] == "running"
    queue = bus.subscribe(run_id) if is_running else None

    async def event_source():
        last_sent = -1
        try:
            for seq, payload_json in db.events_for(run_id):
                if seq > last_sent:
                    yield f"id: {seq}\ndata: {payload_json}\n\n"
                    last_sent = seq

            if queue is None:
                return

            while True:
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=PING_INTERVAL_S)
                except asyncio.TimeoutError:
                    yield ": ping\n\n"
                    continue
                if message is None:  # sentinel: run.close()
                    break
                seq = message["seq"]
                if seq <= last_sent:
                    continue
                last_sent = seq
                yield f"id: {seq}\ndata: {json.dumps(message['payload'])}\n\n"
        finally:
            if queue is not None:
                bus.unsubscribe(run_id, queue)

    return StreamingResponse(
        event_source(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
