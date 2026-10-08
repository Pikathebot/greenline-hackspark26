"""GET /api/cases, POST /api/cases/{id}/runs (docs/05-BACKEND-SPEC.md §1)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from greenline.events.models import BudgetPreset, CaseSummary, RunMode, RunSummary
from greenline.graph.cases import FAILURE_CASES
from greenline.graph.run import DemoRunMissing, RunConflict, RunManager, RunNotFound
from greenline.persistence.db import Database

router = APIRouter()


class StartRunRequest(BaseModel):
    mode: RunMode = "live"
    budget: BudgetPreset = "normal"


def _case_summary(case_id: str, db: Database, demo_runs_dir) -> CaseSummary:
    case = FAILURE_CASES[case_id]
    row = db.last_completed_live(case_id)
    last_run = None
    if row is not None:
        last_run = RunSummary(
            run_id=row["run_id"],
            outcome=row["outcome"],
            duration_ms=row["duration_ms"],
            model_calls=row["model_calls"],
            tool_calls=row["tool_calls"],
            mode=row["mode"],
        )
    has_demo_run = (demo_runs_dir / f"{case_id}.json").exists()
    return CaseSummary(**case.model_dump(), last_run=last_run, has_demo_run=has_demo_run)


@router.get("/api/cases")
async def list_cases(request: Request) -> list[dict]:
    db = request.app.state.db
    demo_runs_dir = request.app.state.settings.demo_runs_path()
    summaries = [_case_summary(case_id, db, demo_runs_dir) for case_id in FAILURE_CASES]
    # Not exclude_none: lastRun is required-but-nullable (RunSummary | null), never omitted.
    return [s.model_dump(by_alias=True, mode="json") for s in summaries]


@router.post("/api/cases/{case_id}/runs")
async def start_run(case_id: str, body: StartRunRequest, request: Request) -> dict:
    run_manager: RunManager = request.app.state.run_manager
    try:
        run_id = await run_manager.start_run(case_id, body.mode, body.budget)
    except RunNotFound:
        raise HTTPException(status_code=404, detail=f"unknown case {case_id!r}")
    except DemoRunMissing:
        raise HTTPException(
            status_code=404, detail=f"no recorded demo run for case {case_id!r}"
        )
    except RunConflict as exc:
        raise HTTPException(
            status_code=409, detail=f"run {exc.active_run_id!r} is already active"
        )
    return {"runId": run_id}
