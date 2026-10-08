"""docs/05-BACKEND-SPEC.md §11: export the best completed live run per
case to demo_runs/<caseId>.json. Fast: seeds runs/events directly, no
Docker or model needed.
"""

from __future__ import annotations

import json

from greenline.demo.export import export_all, export_case, has_mixed_reruns, pick_best_run


def _event(t: int, type_: str, **fields) -> dict:
    return {"t": t, "type": type_, **fields}


def _seed_run(
    db,
    run_id: str,
    case_id: str,
    outcome: str,
    events: list[dict],
    *,
    ended_at: str = "2026-10-08T10:00:00Z",
) -> None:
    db.insert_run(run_id, case_id, "live", "normal", "2026-10-08T09:00:00Z")
    for seq, event in enumerate(events):
        db.insert_event(run_id, seq, event["t"], event["type"], json.dumps(event))
    db.finish_run(
        run_id, status="complete", outcome=outcome, ended_at=ended_at,
        model_calls=1, tool_calls=1, duration_ms=1000,
    )


def _reruns(pattern: list[bool]) -> list[dict]:
    total = len(pattern)
    return [
        _event(i * 100, "rerun.tick", n=i + 1, total=total, passed=p, durationMs=50)
        for i, p in enumerate(pattern)
    ]


def test_has_mixed_reruns():
    assert has_mixed_reruns(_reruns([True, False, True])) is True
    assert has_mixed_reruns(_reruns([True, True, True])) is False
    assert has_mixed_reruns(_reruns([False, False, False])) is False
    assert has_mixed_reruns([]) is False


def test_pick_best_run_matches_expected_outcome(db):
    _seed_run(db, "r1", "0139", "escalated", [_event(0, "run.start", runId="r1", caseId="0139", mode="live", model="m", budgetPreset="normal", caps={"modelCalls": 1, "toolCalls": 1, "elapsedMs": 1})])
    _seed_run(db, "r2", "0139", "reported", [_event(0, "run.start", runId="r2", caseId="0139", mode="live", model="m", budgetPreset="normal", caps={"modelCalls": 1, "toolCalls": 1, "elapsedMs": 1})])

    assert pick_best_run(db, "0139") == "r2"  # 0139's expected outcome is 'reported'


def test_pick_best_run_none_when_no_qualifying_run(db):
    _seed_run(db, "r1", "0137", "escalated", [_event(0, "run.start", runId="r1", caseId="0137", mode="live", model="m", budgetPreset="normal", caps={"modelCalls": 1, "toolCalls": 1, "elapsedMs": 1})])
    # 0137's expected outcome is 'reported' -- the only run is 'escalated'.
    assert pick_best_run(db, "0137") is None


def test_pick_best_run_prefers_mixed_reruns_for_0142(db):
    all_pass = _reruns([True] * 10)
    mixed = _reruns([True, False, True, True, False, True, True, True, False, True])

    _seed_run(db, "r1", "0142", "escalated", all_pass, ended_at="2026-10-08T10:00:00Z")
    _seed_run(db, "r2", "0142", "escalated", mixed, ended_at="2026-10-08T09:30:00Z")  # older, but mixed

    # r2 is older but mixed; r1 is newer but all-pass. Mixed wins.
    assert pick_best_run(db, "0142") == "r2"


def test_pick_best_run_falls_back_to_most_recent_if_none_mixed(db):
    all_pass_1 = _reruns([True] * 10)
    all_pass_2 = _reruns([True] * 10)
    _seed_run(db, "r1", "0142", "escalated", all_pass_1, ended_at="2026-10-08T10:00:00Z")
    _seed_run(db, "r2", "0142", "escalated", all_pass_2, ended_at="2026-10-08T11:00:00Z")

    assert pick_best_run(db, "0142") == "r2"  # most recent, since neither is mixed


def test_export_case_writes_lf_only_json(db, tmp_path):
    events = [
        _event(0, "run.start", runId="r1", caseId="0139", mode="live", model="m", budgetPreset="normal", caps={"modelCalls": 1, "toolCalls": 1, "elapsedMs": 1}),
        _event(100, "done", outcome="reported"),
    ]
    _seed_run(db, "r1", "0139", "reported", events)

    run_id = export_case(db, "0139", tmp_path)
    assert run_id == "r1"

    out_file = tmp_path / "0139.json"
    raw = out_file.read_bytes()
    assert b"\r\n" not in raw

    written = json.loads(out_file.read_text())
    assert written == events


def test_export_case_returns_none_without_a_qualifying_run(db, tmp_path):
    assert export_case(db, "0139", tmp_path) is None
    assert not (tmp_path / "0139.json").exists()


def test_export_all_reports_exported_and_skipped(db, tmp_path):
    events = [_event(0, "done", outcome="reported")]
    _seed_run(db, "r1", "0139", "reported", events)

    result = export_all(db, tmp_path)
    assert result["exported"] == {"0139": "r1"}
    assert set(result["skipped"]) == {"0142", "0144", "0137", "0131", "0128"}


def test_pick_best_run_prefers_the_warm_memory_hit_for_0144(db):
    cold = _reruns([True, False, True, True, False, True, True, True, False, True])
    warm = [_event(0, "memory.hit", caseRef="0142", similarity=0.88, summary="x")]

    _seed_run(db, "r1", "0144", "escalated", cold, ended_at="2026-10-08T11:00:00Z")  # newer, cold
    _seed_run(db, "r2", "0144", "escalated", warm, ended_at="2026-10-08T09:30:00Z")  # older, warm

    assert pick_best_run(db, "0144") == "r2"
