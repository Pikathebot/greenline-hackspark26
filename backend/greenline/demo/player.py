"""Demo player (docs/05-BACKEND-SPEC.md §11).

Re-emits a real, previously recorded run through the same emitter/SSE path,
at its original relative pace. `t` is restamped by the emitter (it's the
only author of `t`), but the gaps between events are preserved. Never calls
the model, Docker or memory -- it must work with only uvicorn running.
"""

from __future__ import annotations

import asyncio
import json

from greenline.config import Settings
from greenline.events.emitter import RunEmitter
from greenline.events.models import BudgetCaps


async def play_demo_run(
    emitter: RunEmitter, case_id: str, settings: Settings, recording: str | None = None
) -> str:
    name = f"{case_id}-{recording}" if recording else case_id
    demo_path = settings.demo_runs_path() / f"{name}.json"
    recorded: list[dict] = json.loads(demo_path.read_text())

    if not recorded or recorded[0]["type"] != "run.start":
        raise ValueError(f"demo_runs/{case_id}.json must start with a run.start event")

    original_start = recorded[0]
    caps = BudgetCaps.model_validate(original_start["caps"])
    # mode is always 'demo' here, regardless of what the recording's own
    # run.start said (it was a real 'live' run when it was captured).
    emitter.start(
        case_id=case_id,
        mode="demo",
        model=original_start["model"],
        budget_preset=original_start["budgetPreset"],
        caps=caps,
    )

    outcome = "error"
    previous_t = original_start["t"]
    for raw_event in recorded[1:]:
        gap_ms = max(0, raw_event["t"] - previous_t)
        previous_t = raw_event["t"]
        if gap_ms:
            await asyncio.sleep((gap_ms / 1000.0) / settings.demo_speed)

        event_type = raw_event["type"]
        # The recorded fields are already camelCase (the wire format), which
        # the contract's alias_generator accepts directly as validation input
        # (populate_by_name only ADDS the snake_case names; aliases still work).
        fields = {key: value for key, value in raw_event.items() if key not in ("t", "type")}
        emitter.emit(event_type, **fields)

        if event_type == "done":
            outcome = fields["outcome"]

    return outcome
