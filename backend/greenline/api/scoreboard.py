"""GET /api/scoreboard (docs/05-BACKEND-SPEC.md §10). Computed from
completed LIVE runs only (demo runs excluded by construction --
Database.all_completed_live_runs() filters mode='live'). Every metric is
null when its sample is empty -- never a fabricated number.
"""

from __future__ import annotations

import json
import statistics
from collections import defaultdict

from fastapi import APIRouter, Request

from greenline.events.models import CamelModel
from greenline.graph.cases import FAILURE_CASES
from greenline.persistence.db import Database

router = APIRouter()

# Human-judgment metrics: permanently out of scope for this build, not
# merely unmeasured-for-now (unlike e.g. patchSuccessRate, which is null
# only because the sample is still small).
NOT_MEASURED = ["falsePrRate", "humanBaseline"]


class WarmVsCold(CamelModel):
    cold_ms: float | None = None
    warm_ms: float | None = None
    cold_tool_calls: float | None = None
    warm_tool_calls: float | None = None


class ScoreboardMetrics(CamelModel):
    triage_accuracy: float | None = None
    patch_success_rate: float | None = None
    escalation_rate: float | None = None
    median_time_to_verdict_ms: float | None = None
    p95_duration_ms: float | None = None
    avg_model_calls: float | None = None
    avg_tool_calls: float | None = None
    warm_vs_cold: WarmVsCold = WarmVsCold()


class PerCaseStats(CamelModel):
    case_id: str
    runs: int
    last_outcome: str | None = None
    median_duration_ms: float | None = None


class Scoreboard(CamelModel):
    sample_size: int
    metrics: ScoreboardMetrics
    matrix: dict[str, dict[str, int]]
    per_case: list[PerCaseStats]
    not_measured: list[str]
    note: str


def _percentile(values: list[float], pct: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    k = (len(ordered) - 1) * pct
    lo = int(k)
    hi = min(lo + 1, len(ordered) - 1)
    if lo == hi:
        return ordered[lo]
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (k - lo)


def _run_facts(db: Database, run_id: str) -> dict:
    """Pulls verdict.cls (+ its own t, for time-to-verdict) and every
    patch.attempt.result out of a run's persisted events."""
    verdict_cls = None
    verdict_t = None
    patch_results: list[str] = []
    for _seq, payload_json in db.events_for(run_id):
        event = json.loads(payload_json)
        if event["type"] == "verdict":
            verdict_cls = event["cls"]
            verdict_t = event["t"]
        elif event["type"] == "patch.attempt":
            patch_results.append(event["result"])
    return {"verdict_cls": verdict_cls, "verdict_t": verdict_t, "patch_results": patch_results}


def compute_scoreboard(db: Database) -> Scoreboard:
    runs = db.all_completed_live_runs()
    sample_size = len(runs)
    facts_by_run = {row["run_id"]: _run_facts(db, row["run_id"]) for row in runs}

    def rows_for(case_id: str) -> list:
        return [row for row in runs if row["case_id"] == case_id]

    # -- triageAccuracy + matrix (invariant 4: some runs have no verdict) --
    matrix: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    correct = with_verdict = 0
    for row in runs:
        predicted = facts_by_run[row["run_id"]]["verdict_cls"]
        if predicted is None:
            continue
        actual = FAILURE_CASES[row["case_id"]].cls
        matrix[actual][predicted] += 1
        with_verdict += 1
        correct += predicted == actual
    triage_accuracy = (correct / with_verdict) if with_verdict else None

    # -- patchSuccessRate: reported / runs with a non-vetoed patch attempt --
    runs_with_patch_attempt = reported_with_patch_attempt = 0
    for row in runs:
        if any(r != "vetoed" for r in facts_by_run[row["run_id"]]["patch_results"]):
            runs_with_patch_attempt += 1
            reported_with_patch_attempt += row["outcome"] == "reported"
    patch_success_rate = (
        (reported_with_patch_attempt / runs_with_patch_attempt) if runs_with_patch_attempt else None
    )

    # -- escalationRate --
    escalated_count = sum(1 for row in runs if row["outcome"] == "escalated")
    escalation_rate = (escalated_count / sample_size) if sample_size else None

    # -- medianTimeToVerdictMs --
    verdict_ts = [f["verdict_t"] for f in facts_by_run.values() if f["verdict_t"] is not None]
    median_time_to_verdict_ms = statistics.median(verdict_ts) if verdict_ts else None

    # -- p95DurationMs, avgModelCalls, avgToolCalls --
    durations = [float(row["duration_ms"]) for row in runs if row["duration_ms"] is not None]
    p95_duration_ms = _percentile(durations, 0.95)
    model_calls = [row["model_calls"] for row in runs]
    tool_calls = [row["tool_calls"] for row in runs]
    avg_model_calls = (sum(model_calls) / len(model_calls)) if model_calls else None
    avg_tool_calls = (sum(tool_calls) / len(tool_calls)) if tool_calls else None

    # -- warmVsCold: 0142 (cold) vs 0144 (warm) --
    cold_rows, warm_rows = rows_for("0142"), rows_for("0144")
    warm_vs_cold = WarmVsCold(
        cold_ms=statistics.median([r["duration_ms"] for r in cold_rows]) if cold_rows else None,
        warm_ms=statistics.median([r["duration_ms"] for r in warm_rows]) if warm_rows else None,
        cold_tool_calls=statistics.median([r["tool_calls"] for r in cold_rows]) if cold_rows else None,
        warm_tool_calls=statistics.median([r["tool_calls"] for r in warm_rows]) if warm_rows else None,
    )

    # -- perCase: one row per case, including cases with zero runs so far --
    per_case = []
    for case_id in FAILURE_CASES:
        case_rows = rows_for(case_id)
        if case_rows:
            last_outcome = max(case_rows, key=lambda r: r["ended_at"])["outcome"]
            median_duration_ms = statistics.median([r["duration_ms"] for r in case_rows])
        else:
            last_outcome = None
            median_duration_ms = None
        per_case.append(
            PerCaseStats(
                case_id=case_id, runs=len(case_rows), last_outcome=last_outcome,
                median_duration_ms=median_duration_ms,
            )
        )

    note = (
        f"Computed from {sample_size} completed live run(s). falsePrRate and humanBaseline "
        "need external review and are never measured by this build."
    )

    return Scoreboard(
        sample_size=sample_size,
        metrics=ScoreboardMetrics(
            triage_accuracy=triage_accuracy,
            patch_success_rate=patch_success_rate,
            escalation_rate=escalation_rate,
            median_time_to_verdict_ms=median_time_to_verdict_ms,
            p95_duration_ms=p95_duration_ms,
            avg_model_calls=avg_model_calls,
            avg_tool_calls=avg_tool_calls,
            warm_vs_cold=warm_vs_cold,
        ),
        matrix={actual: dict(predicted) for actual, predicted in matrix.items()},
        per_case=per_case,
        not_measured=NOT_MEASURED,
        note=note,
    )


@router.get("/api/scoreboard")
async def scoreboard(request: Request) -> dict:
    db = request.app.state.db
    return compute_scoreboard(db).model_dump(by_alias=True, mode="json")
