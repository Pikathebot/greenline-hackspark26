"""B2 acceptance: a run that raises still ends with exactly one done{outcome:'error'}.

The real graph lands at B7; until then a live run's `_run_live` always raises
NotImplementedError, which exercises the whole error path end to end.
"""

from __future__ import annotations

import asyncio

import pytest

from greenline.config import Settings
from greenline.graph.run import DemoRunMissing, RunConflict, RunManager, RunNotFound


@pytest.fixture
def settings(tmp_path) -> Settings:
    return Settings(_env_file=None, db_path=str(tmp_path / "test.db"))


async def test_live_run_that_raises_ends_in_single_done_error(db, bus, settings):
    manager = RunManager(db, bus, settings)
    run_id = await manager.start_run("0142", mode="live", budget_preset="normal")

    queue = bus.subscribe(run_id)
    events = []
    while True:
        message = await asyncio.wait_for(queue.get(), timeout=5)
        if message is None:
            break
        events.append(message["payload"])

    assert events[0]["type"] == "run.start"
    done_events = [e for e in events if e["type"] == "done"]
    assert len(done_events) == 1
    assert done_events[-1]["outcome"] == "error"
    assert events[-1]["type"] == "done"  # done is last

    error_events = [e for e in events if e["type"] == "error"]
    assert len(error_events) == 1

    run_row = db.get_run(run_id)
    assert run_row["status"] == "error"
    assert run_row["outcome"] == "error"
    assert run_row["ended_at"] is not None

    # No run stays active after it finishes.
    assert manager.active is None


async def test_unknown_case_raises_run_not_found(db, bus, settings):
    manager = RunManager(db, bus, settings)
    with pytest.raises(RunNotFound):
        await manager.start_run("9999", mode="live", budget_preset="normal")


async def test_demo_mode_without_recorded_run_raises(db, bus, settings):
    manager = RunManager(db, bus, settings)
    with pytest.raises(DemoRunMissing):
        await manager.start_run("0142", mode="demo", budget_preset="normal")


async def test_second_run_while_active_conflicts(db, bus, settings):
    manager = RunManager(db, bus, settings)
    run_id = await manager.start_run("0142", mode="live", budget_preset="normal")
    with pytest.raises(RunConflict):
        await manager.start_run("0144", mode="live", budget_preset="normal")

    # drain the first run so it finishes cleanly (avoids a dangling task warning)
    queue = bus.subscribe(run_id)
    while True:
        message = await asyncio.wait_for(queue.get(), timeout=5)
        if message is None:
            break
