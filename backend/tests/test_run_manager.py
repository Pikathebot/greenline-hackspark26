"""B2 acceptance: a run that raises still ends with exactly one done{outcome:'error'}.

This test deliberately runs RunManager in isolation, without the FastAPI
lifespan that calls init_llm_client(), so `_run_live` hits
get_llm_client()'s RuntimeError while building the initial graph state --
a convenient, honest way to exercise the whole error path end to end
without Docker or a model server. The real graph's happy/escalation paths
are covered by tests/test_graph.py (@pytest.mark.slow).
"""

from __future__ import annotations

import asyncio

import pytest

from greenline.config import Settings
from greenline.graph.run import DemoRunMissing, RunConflict, RunManager, RunNotFound


@pytest.fixture
def settings(tmp_path) -> Settings:
    # demo_runs_dir points at an empty tmp dir, not the real backend/demo_runs/
    # -- tests must never depend on which cases happen to have a real
    # recording on disk at the moment (B12 exported several for real).
    return Settings(
        _env_file=None,
        db_path=str(tmp_path / "test.db"),
        demo_runs_dir=str(tmp_path / "demo_runs"),
    )


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
    # `settings` points demo_runs_dir at an empty tmp dir, so no case has
    # a recording here regardless of which cases have a real export in
    # the actual backend/demo_runs/ right now.
    manager = RunManager(db, bus, settings)
    with pytest.raises(DemoRunMissing):
        await manager.start_run("0144", mode="demo", budget_preset="normal")


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
