"""B3 acceptance: POST runs {mode:'demo'} streams paced events and closes
after done (docs/05-BACKEND-SPEC.md §12.6). Uses whatever recording is
currently at demo_runs/0142.json (hand-written at B3, replaced by a real
export once 0142 ran live, per docs/05 §11), sped up so the test doesn't
take however long that recording's wall-clock pacing was."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from greenline.config import get_settings
from greenline.persistence import db as db_module


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("GREENLINE_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("GREENLINE_DEMO_SPEED", "2000")  # ~23s recording -> ~12ms
    get_settings.cache_clear()
    db_module.reset_db_for_tests()

    from greenline.main import app

    with TestClient(app) as test_client:
        yield test_client

    get_settings.cache_clear()
    db_module.reset_db_for_tests()


def test_demo_run_streams_and_closes_at_done(client: TestClient):
    start_resp = client.post("/api/cases/0142/runs", json={"mode": "demo"})
    assert start_resp.status_code == 200
    run_id = start_resp.json()["runId"]

    events = []
    with client.stream("GET", f"/api/runs/{run_id}/stream") as stream_resp:
        assert stream_resp.status_code == 200
        assert stream_resp.headers["cache-control"] == "no-cache"
        # Deliberately does NOT break on the first `done`: the server must
        # close the stream itself (invariant 1, exactly one done), so reading
        # to the end of the response is what actually proves that.
        for line in stream_resp.iter_lines():
            if not line.startswith("data:"):
                continue
            event = json.loads(line[len("data:") :].strip())
            events.append(event)

    assert events[0]["type"] == "run.start"
    assert events[0]["mode"] == "demo"
    assert events[-1]["type"] == "done"
    assert events[-1]["outcome"] == "escalated"
    done_events = [e for e in events if e["type"] == "done"]
    assert len(done_events) == 1

    # the demo player never calls the model/docker/memory, and it re-emits
    # exactly the recorded events (minus the original run.start).
    with open("demo_runs/0142.json") as f:
        recorded = json.load(f)
    assert len(events) == len(recorded)


@pytest.fixture
def client_without_demo_runs(tmp_path, monkeypatch):
    # Points demo_runs_dir at an empty tmp dir, so this is decoupled from
    # which cases happen to have a real recording in the actual
    # backend/demo_runs/ right now (B12 exported several for real).
    monkeypatch.setenv("GREENLINE_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("GREENLINE_DEMO_RUNS_DIR", str(tmp_path / "demo_runs"))
    get_settings.cache_clear()
    db_module.reset_db_for_tests()

    from greenline.main import app

    with TestClient(app) as test_client:
        yield test_client

    get_settings.cache_clear()
    db_module.reset_db_for_tests()


def test_demo_run_missing_case_file_is_404(client_without_demo_runs: TestClient):
    resp = client_without_demo_runs.post("/api/cases/0144/runs", json={"mode": "demo"})
    assert resp.status_code == 404
