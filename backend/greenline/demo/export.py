"""Export the best completed live run per case to demo_runs/<caseId>.json
(docs/05-BACKEND-SPEC.md §11). Shared by scripts/export_demo_runs.py and
POST /api/admin/export-demo-runs ("same logic as the script").

EXPECTED_OUTCOME is demo-curation metadata -- it picks which of a case's
completed runs makes the best exemplar to SHOW, after the fact. It is
never read by the graph itself (docs/02-DECISIONS lesson): the graph
produces whatever outcome a real run produces, and this module just
chooses the best one already sitting in the database to export.
"""

from __future__ import annotations

import json
from pathlib import Path

from greenline.graph.cases import FAILURE_CASES
from greenline.persistence.db import Database

EXPECTED_OUTCOME = {
    "0142": "escalated",
    "0144": "escalated",
    "0139": "reported",
    "0137": "reported",
    "0131": "reported",
    "0128": "escalated",
}

# For these cases specifically, prefer a run with a genuinely mixed rerun
# distribution (0 < fails < total) -- the hero beat needs to show real
# ambiguity, not a lucky all-pass or all-fail sample.
PREFER_MIXED_RERUNS = {"0142"}

# #0144's beat is the warm skip: prefer a run that recalled #0142 (memory.hit).
# A warm run has no rerun ticks, so it can never be "mixed" -- hence a separate rule.
PREFER_MEMORY_HIT = {"0144"}


def events_for_run(db: Database, run_id: str) -> list[dict]:
    return [json.loads(payload_json) for _seq, payload_json in db.events_for(run_id)]


def has_mixed_reruns(events: list[dict]) -> bool:
    ticks = [e for e in events if e["type"] == "rerun.tick"]
    if not ticks:
        return False
    total = ticks[0]["total"]
    fails = sum(1 for tick in ticks if not tick["passed"])
    return 0 < fails < total


def pick_best_run(db: Database, case_id: str) -> str | None:
    expected_outcome = EXPECTED_OUTCOME[case_id]
    candidates = [r for r in db.runs_for_case(case_id, mode="live") if r["outcome"] == expected_outcome]
    if not candidates:
        return None

    if case_id in PREFER_MIXED_RERUNS:
        mixed = [r for r in candidates if has_mixed_reruns(events_for_run(db, r["run_id"]))]
        if mixed:
            candidates = mixed

    if case_id in PREFER_MEMORY_HIT:
        warm = [
            r for r in candidates
            if any(e["type"] == "memory.hit" for e in events_for_run(db, r["run_id"]))
        ]
        if warm:
            candidates = warm

    candidates.sort(key=lambda r: r["ended_at"], reverse=True)
    return candidates[0]["run_id"]


def export_case(db: Database, case_id: str, demo_runs_dir: Path) -> str | None:
    run_id = pick_best_run(db, case_id)
    if run_id is None:
        return None
    events = events_for_run(db, run_id)
    demo_runs_dir.mkdir(parents=True, exist_ok=True)
    out_path = demo_runs_dir / f"{case_id}.json"
    out_path.write_text(json.dumps(events, indent=2) + "\n", encoding="utf-8", newline="\n")
    return run_id


def export_all(db: Database, demo_runs_dir: Path) -> dict:
    exported: dict[str, str] = {}
    skipped: list[str] = []
    for case_id in FAILURE_CASES:
        run_id = export_case(db, case_id, demo_runs_dir)
        if run_id is None:
            skipped.append(case_id)
        else:
            exported[case_id] = run_id
    return {"exported": exported, "skipped": skipped}
