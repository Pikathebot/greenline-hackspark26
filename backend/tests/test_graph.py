"""B7 acceptance (docs/10-BUILD-PLAN.md): #0142 live ends `escalated` with
`protected_file` fired. First event run.start, exactly one done.

Needs the real llama-server and Docker -- excluded from the default
`pytest` run. Run explicitly:
    .venv\\Scripts\\python.exe -m pytest -m slow tests\\test_graph.py -v
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from greenline.config import Settings, get_settings
from greenline.persistence import db as db_module
from tests._invariants import assert_contract_invariants

pytestmark = pytest.mark.slow


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("GREENLINE_DB_PATH", str(tmp_path / "test.db"))
    get_settings.cache_clear()
    db_module.reset_db_for_tests()

    from greenline.main import app

    with TestClient(app) as test_client:
        yield test_client

    get_settings.cache_clear()
    db_module.reset_db_for_tests()


def _run_live(client: TestClient, case_id: str, budget: str = "normal") -> list[dict]:
    start_resp = client.post(f"/api/cases/{case_id}/runs", json={"mode": "live", "budget": budget})
    assert start_resp.status_code == 200
    run_id = start_resp.json()["runId"]

    events = []
    with client.stream("GET", f"/api/runs/{run_id}/stream", timeout=120) as stream_resp:
        assert stream_resp.status_code == 200
        for line in stream_resp.iter_lines():
            if not line.startswith("data:"):
                continue
            events.append(json.loads(line[len("data:") :].strip()))
    return events


def _assert_structural_invariants(events: list[dict]) -> None:
    """These must hold on EVERY run, no matter which class the model lands
    on -- unlike the semantic checks in test_0142, these are never retried.
    docs/04's generic invariants 1-6 are shared with test_termination.py;
    the rest here are extra checks specific to a live run."""
    assert_contract_invariants(events)
    assert events[0]["mode"] == "live"

    error_events = [e for e in events if e["type"] == "error"]
    assert error_events == []  # a real escalation, not a crash

    guardrails = [e for e in events if e["type"] == "guardrail"]
    no_creds = [g for g in guardrails if g["rail"] == "no_creds"][0]
    egress_off = [g for g in guardrails if g["rail"] == "egress_off"][0]
    assert no_creds["fired"] is False
    assert egress_off["fired"] is False

    reports = [e for e in events if e["type"] == "report"]
    assert len(reports) == 1


def test_0142_live_escalates_with_protected_file(client: TestClient):
    # #0142 is deliberately probabilistic (~30% failure per sandbox process,
    # by design -- docs/06-FIXTURE-REPO-SPEC.md). The structural invariants
    # below must hold on the very first try, always. The semantic verdict
    # (flaky + protected_file) is retried a few times because asserting an
    # exact outcome from an inherently random case needs that -- this is
    # the same thing a human would do at the demo if unlucky.
    last_events: list[dict] = []
    for attempt in range(3):
        events = _run_live(client, "0142")
        last_events = events
        _assert_structural_invariants(events)

        done = next(e for e in events if e["type"] == "done")
        guardrails = [e for e in events if e["type"] == "guardrail"]
        protected_file_events = [g for g in guardrails if g["rail"] == "protected_file"]
        verdicts = [e for e in events if e["type"] == "verdict"]

        if (
            done["outcome"] == "escalated"
            and len(protected_file_events) == 1
            and protected_file_events[0]["fired"] is True
            and len(verdicts) == 1
            and verdicts[0]["cls"] == "flaky"
        ):
            rerun_ticks = [e for e in events if e["type"] == "rerun.tick"]
            assert len(rerun_ticks) == 10
            assert [t["n"] for t in rerun_ticks] == list(range(1, 11))
            reports = [e for e in events if e["type"] == "report"]
            assert reports[0]["kind"] == "escalation"
            return

    pytest.fail(
        f"0142 didn't land on escalated/flaky/protected_file across 3 live "
        f"attempts; last run's verdict events: "
        f"{[e for e in last_events if e['type'] == 'verdict']}"
    )


def test_0128_env_has_no_safe_fix(client: TestClient):
    # 0128 is deterministic (KeyError every time), so no retry needed here.
    events = _run_live(client, "0128")
    _assert_structural_invariants(events)

    done = next(e for e in events if e["type"] == "done")
    assert done["outcome"] == "escalated"

    verdicts = [e for e in events if e["type"] == "verdict"]
    assert len(verdicts) == 1
    assert verdicts[0]["cls"] == "env"

    reports = [e for e in events if e["type"] == "report"]
    assert reports[0]["kind"] == "escalation"
    assert reports[0]["body"]  # the Reporter must never produce an empty note

    # no patch_target for 0128 -> blocked via no_safe_fix, not protected_file
    protected_file_events = [
        e for e in events if e["type"] == "guardrail" and e["rail"] == "protected_file"
    ]
    assert protected_file_events == []


def test_0139_dependency_reaches_reported(client: TestClient):
    """B9 acceptance: #0139 -> reported (the model-authored happy path)."""
    events = _run_live(client, "0139")
    _assert_structural_invariants(events)

    done = next(e for e in events if e["type"] == "done")
    assert done["outcome"] == "reported", f"0139 didn't report: {events}"

    patch_attempts = [e for e in events if e["type"] == "patch.attempt"]
    assert patch_attempts, "no patch attempt was made"
    assert patch_attempts[0]["source"] == "model"
    assert patch_attempts[0]["result"] == "green"

    reports = [e for e in events if e["type"] == "report"]
    assert reports[0]["kind"] == "pr"
    assert reports[0]["dryRun"] is True
    assert "prUrl" in reports[0]


def test_0131_lint_reaches_reported_via_tool_fix(client: TestClient):
    """B9 acceptance: #0131 -> reported, source:'tool' (0 model calls for
    the patch itself -- ruff --fix)."""
    events = _run_live(client, "0131")
    _assert_structural_invariants(events)

    done = next(e for e in events if e["type"] == "done")
    assert done["outcome"] == "reported", f"0131 didn't report: {events}"

    patch_attempts = [e for e in events if e["type"] == "patch.attempt"]
    assert patch_attempts[0]["source"] == "tool"
    assert patch_attempts[0]["result"] == "green"

    critic_votes = [e for e in events if e["type"] == "critic.vote"]
    assert len(critic_votes[0]["samples"]) == 1  # k=1 for a tool-sourced diff

    reports = [e for e in events if e["type"] == "report"]
    assert reports[0]["kind"] == "pr"


def test_0137_regression_reaches_reported(client: TestClient):
    """B9 acceptance: #0137 -> reported (a Critic loop is acceptable).
    Retried for the same reason as 0142: an LLM-authored fix and an LLM
    critic vote are both probabilistic, unlike 0139/0131's simpler fixes."""
    last_events: list[dict] = []
    for _attempt in range(3):
        events = _run_live(client, "0137")
        last_events = events
        _assert_structural_invariants(events)
        done = next(e for e in events if e["type"] == "done")
        if done["outcome"] == "reported":
            patch_attempts = [e for e in events if e["type"] == "patch.attempt"]
            assert 1 <= len(patch_attempts) <= 2
            reports = [e for e in events if e["type"] == "report"]
            assert reports[0]["kind"] == "pr"
            return

    pytest.fail(
        "0137 didn't reach reported across 3 live attempts; last run's "
        f"patch/critic/done events: "
        f"{[e for e in last_events if e['type'] in ('patch.attempt', 'critic.vote', 'done')]}"
    )


def test_0128_tight_budget_exhausted(client: TestClient):
    """B11 acceptance: #0128 tight -> budget_exhausted with a report.
    docs/05 §9's own expected shape: R(budget hit after 2 reruns), 2 model
    calls, 3 sandbox runs. Real stack -- B8 only proved this with fakes."""
    tight_caps = Settings(_env_file=None).caps("tight")

    events = _run_live(client, "0128", budget="tight")
    _assert_structural_invariants(events)

    start = events[0]
    assert start["budgetPreset"] == "tight"
    assert start["caps"]["modelCalls"] == tight_caps.model_calls
    assert start["caps"]["toolCalls"] == tight_caps.tool_calls
    assert start["caps"]["elapsedMs"] == tight_caps.elapsed_ms

    done = next(e for e in events if e["type"] == "done")
    assert done["outcome"] == "budget_exhausted", f"0128 tight: {events}"

    # docs/05 §9: "R(budget hit after 2 reruns)" -- watcher's 1 tool call +
    # 2 reruns = 3 (the tight cap), so check_budget raises before a 3rd.
    rerun_ticks = [e for e in events if e["type"] == "rerun.tick"]
    assert len(rerun_ticks) == tight_caps.tool_calls - 1

    reports = [e for e in events if e["type"] == "report"]
    assert len(reports) == 1
    assert reports[0]["body"]  # the Reporter must never produce an empty note


def test_0139_tight_budget_also_exhausts_gracefully(client: TestClient):
    """Robustness check, not a named ticket line: confirms the real tight
    preset doesn't crash into 'error' for a DIFFERENT, Patcher-eligible
    case either (not just 0128). It turns out to exhaust at the exact same
    point as 0128 -- the real tight tool_calls cap (3) is simply too tight
    for ANY dependency/regression/env-classed case to ever reach Patcher
    (watcher's 1 + at most 2 of N=3 reruns already hits it), confirmed by
    tracing the actual event stream. The check_budget() call sites inside
    Patcher/Critic specifically are covered precisely, with custom caps
    that let them be reached, by test_termination.py's fake-driven
    test_tight_model_calls_exhausts_at_patcher_entry and
    test_tight_model_calls_exhausts_inside_critic_sampling."""
    events = _run_live(client, "0139", budget="tight")
    _assert_structural_invariants(events)

    done = next(e for e in events if e["type"] == "done")
    assert done["outcome"] == "budget_exhausted", f"0139 tight: {events}"
    assert [e for e in events if e["type"] == "patch.attempt"] == []  # never reached Patcher
