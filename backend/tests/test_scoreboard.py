"""docs/05-BACKEND-SPEC.md §10: GET /api/scoreboard, computed from
completed LIVE runs only. Fast: seeds runs/events directly via Database,
no Docker or model needed.
"""

from __future__ import annotations

import json

import pytest

from greenline.api.scoreboard import compute_scoreboard


def _event(t: int, type_: str, **fields) -> str:
    return json.dumps({"t": t, "type": type_, **fields})


def _seed_run(
    db,
    run_id: str,
    case_id: str,
    outcome: str,
    *,
    verdict_cls: str | None = None,
    verdict_t: int = 1000,
    patch_results: tuple[str, ...] = (),
    model_calls: int = 1,
    tool_calls: int = 1,
    duration_ms: int = 1000,
    ended_at: str = "2026-10-08T10:00:00Z",
) -> None:
    db.insert_run(run_id, case_id, "live", "normal", "2026-10-08T09:00:00Z")
    seq = 0
    if verdict_cls is not None:
        db.insert_event(
            run_id, seq, verdict_t, "verdict",
            _event(verdict_t, "verdict", cls=verdict_cls, confidence=0.9, rationale="x"),
        )
        seq += 1
    for n, result in enumerate(patch_results, start=1):
        db.insert_event(
            run_id, seq, 0, "patch.attempt",
            _event(0, "patch.attempt", n=n, file="x.py", diff="d", source="model", result=result),
        )
        seq += 1
    db.finish_run(
        run_id, status="complete", outcome=outcome, ended_at=ended_at,
        model_calls=model_calls, tool_calls=tool_calls, duration_ms=duration_ms,
    )


@pytest.fixture
def seeded(db):
    # 0142 (cold, flaky, ground truth=flaky): 2 escalated runs.
    _seed_run(db, "r1", "0142", "escalated", verdict_cls="flaky", duration_ms=20_000, tool_calls=11, ended_at="2026-10-08T10:00:00Z")
    _seed_run(db, "r2", "0142", "escalated", verdict_cls="flaky", duration_ms=24_000, tool_calls=11, ended_at="2026-10-08T10:05:00Z")
    # 0144 (warm, flaky): 1 escalated run, much cheaper.
    _seed_run(db, "r3", "0144", "escalated", verdict_cls="flaky", duration_ms=9_000, tool_calls=1, ended_at="2026-10-08T10:10:00Z")
    # 0139 (ground truth=dependency): one reported (patch green), one
    # escalated despite a patch attempt (patch red) -- and misclassified
    # by the model (verdict says regression, not dependency).
    _seed_run(db, "r4", "0139", "reported", verdict_cls="dependency", patch_results=("green",), duration_ms=15_000, ended_at="2026-10-08T10:15:00Z")
    _seed_run(db, "r5", "0139", "escalated", verdict_cls="regression", patch_results=("red",), duration_ms=16_000, ended_at="2026-10-08T10:20:00Z")
    # 0128: budget_exhausted, no verdict at all (invariant 4).
    _seed_run(db, "r6", "0128", "budget_exhausted", verdict_cls=None, duration_ms=5_000, model_calls=2, tool_calls=3, ended_at="2026-10-08T10:25:00Z")
    return db


def test_sample_size_matches_seeded_runs(seeded):
    board = compute_scoreboard(seeded)
    assert board.sample_size == 6


def test_triage_accuracy_excludes_verdict_less_runs(seeded):
    board = compute_scoreboard(seeded)
    # 5 of 6 runs have a verdict (r6 doesn't); 4 of those 5 match ground truth.
    assert board.metrics.triage_accuracy == pytest.approx(4 / 5)


def test_confusion_matrix_shape(seeded):
    board = compute_scoreboard(seeded)
    assert board.matrix["flaky"]["flaky"] == 3  # r1, r2, r3
    assert board.matrix["dependency"]["dependency"] == 1  # r4
    assert board.matrix["dependency"]["regression"] == 1  # r5, misclassified
    assert "env" not in board.matrix  # r6 had no verdict at all


def test_patch_success_rate(seeded):
    board = compute_scoreboard(seeded)
    # 2 runs had a non-vetoed patch attempt (r4, r5); only r4 was reported.
    assert board.metrics.patch_success_rate == pytest.approx(0.5)


def test_escalation_rate(seeded):
    board = compute_scoreboard(seeded)
    # escalated: r1, r2, r3, r5 = 4 of 6.
    assert board.metrics.escalation_rate == pytest.approx(4 / 6)


def test_warm_vs_cold(seeded):
    board = compute_scoreboard(seeded)
    wvc = board.metrics.warm_vs_cold
    assert wvc.cold_ms == pytest.approx(22_000)  # median(20000, 24000)
    assert wvc.warm_ms == pytest.approx(9_000)
    assert wvc.cold_tool_calls == pytest.approx(11)
    assert wvc.warm_tool_calls == pytest.approx(1)


def test_per_case_includes_zero_run_cases(seeded):
    board = compute_scoreboard(seeded)
    by_case = {row.case_id: row for row in board.per_case}
    assert by_case["0142"].runs == 2
    assert by_case["0139"].runs == 2
    assert by_case["0128"].runs == 1
    # 0131 and 0137 never ran in this fixture -- zero, not fabricated.
    assert by_case["0131"].runs == 0
    assert by_case["0131"].last_outcome is None
    assert by_case["0131"].median_duration_ms is None


def test_not_measured_is_always_present(seeded):
    board = compute_scoreboard(seeded)
    assert board.not_measured == ["falsePrRate", "humanBaseline"]


def test_empty_db_gives_null_metrics_not_fabricated_numbers(db):
    board = compute_scoreboard(db)
    assert board.sample_size == 0
    assert board.metrics.triage_accuracy is None
    assert board.metrics.patch_success_rate is None
    assert board.metrics.escalation_rate is None
    assert board.metrics.median_time_to_verdict_ms is None
    assert board.metrics.p95_duration_ms is None
    assert board.metrics.avg_model_calls is None
    assert board.metrics.avg_tool_calls is None
    assert board.metrics.warm_vs_cold.cold_ms is None
    assert board.matrix == {}
    assert all(row.runs == 0 for row in board.per_case)


def test_demo_runs_are_excluded(db):
    # Demo-mode runs must never pollute the scoreboard.
    db.insert_run("demo-1", "0142", "demo", "normal", "2026-10-08T09:00:00Z")
    db.finish_run("demo-1", status="complete", outcome="escalated", ended_at="2026-10-08T09:01:00Z", model_calls=3, tool_calls=11, duration_ms=23_000)
    board = compute_scoreboard(db)
    assert board.sample_size == 0
