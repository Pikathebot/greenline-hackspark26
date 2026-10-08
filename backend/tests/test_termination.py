"""B8 (docs/05-BACKEND-SPEC.md §12.5): "the most valuable test". Runs the
REAL graph (real RunEmitter, db, bus, RunManager) with a fake LLM and a
fake sandbox standing in for the model server and Docker, across all six
cases plus a tight-budget 0128. Fast: no GPU, no Docker.
"""

from __future__ import annotations

import asyncio

import pytest

from greenline.config import Settings
from greenline.graph.cases import CaseConfig, rerun_count_for
from greenline.graph.run import RunManager
from greenline.llm.schemas import AnalystOutput, ReportOutput, TriageOutput
from greenline.sandbox.runner import SandboxRunner, TestResult
from tests._invariants import assert_contract_invariants


class FakeLLM:
    """Stands in for LLMClient: one canned response per schema class."""

    def __init__(self, responses: dict[type, object]) -> None:
        self._responses = responses
        self.calls: list[type] = []

    async def complete(self, system: str, user: str, schema: type, temperature: float):
        self.calls.append(schema)
        return self._responses[schema]


class FakeSandbox:
    """Stands in for SandboxRunner: scripted run_ci + run_test results."""

    def __init__(self, ci_result: TestResult, rerun_results: list[TestResult]) -> None:
        self._ci_result = ci_result
        self._rerun_results = list(rerun_results)
        self.run_ci_calls = 0
        self.run_test_calls = 0

    def run_ci(self, branch: str) -> TestResult:
        self.run_ci_calls += 1
        return self._ci_result

    def run_test(self, branch: str, nodeid: str) -> TestResult:
        self.run_test_calls += 1
        if not self._rerun_results:
            raise AssertionError(
                f"run_test called more times ({self.run_test_calls}) than scripted "
                f"({self.run_test_calls - 1}) -- the graph over-consumed the budget"
            )
        return self._rerun_results.pop(0)

    @staticmethod
    def construction_kwargs() -> dict:
        return SandboxRunner.construction_kwargs()


def _tr(passed: bool, stdout: str = "") -> TestResult:
    return TestResult(
        passed=passed, exit_code=0 if passed else 1, stdout=stdout, stderr="", duration_ms=50, command="fake"
    )


async def _run_with_fakes(db, bus, settings, case_id, budget_preset, llm, sandbox) -> list[dict]:
    manager = RunManager(
        db, bus, settings, sandbox_factory=lambda: sandbox, llm_factory=lambda: llm
    )
    run_id = await manager.start_run(case_id, mode="live", budget_preset=budget_preset)

    queue = bus.subscribe(run_id)
    events: list[dict] = []
    while True:
        message = await asyncio.wait_for(queue.get(), timeout=5)
        if message is None:
            break
        events.append(message["payload"])
    return events


def _llm_for(cls: str) -> FakeLLM:
    return FakeLLM(
        {
            TriageOutput: TriageOutput(cls=cls, rationale="fake triage rationale"),
            AnalystOutput: AnalystOutput(cls=cls, rationale="fake analyst rationale", evidence_strength="strong"),
            ReportOutput: ReportOutput(title="fake title", body="fake body"),
        }
    )


# cls here only picks which canned Triage/Analyst response the FAKE returns
# -- test data, not something the graph itself reads (invariant 7).
CASE_SCRIPTS = {
    "0142": dict(cls="flaky", ci_log="TimeoutError: settlement reconciliation exceeded timeout=0.5s"),
    "0144": dict(cls="flaky", ci_log="TimeoutError: payout reconciliation exceeded timeout=0.5s"),
    "0139": dict(cls="dependency", ci_log="ImportError: cannot import name 'Retry'"),
    "0137": dict(cls="regression", ci_log="AssertionError: assert True is False"),
    "0131": dict(cls="lint", ci_log="F401 'json' imported but unused\nI001 import block is un-sorted"),
    "0128": dict(cls="env", ci_log="KeyError: 'LEDGER_REGION'"),
}


@pytest.mark.parametrize("case_id", list(CASE_SCRIPTS))
async def test_graph_terminates_with_valid_contract(db, bus, case_id):
    script = CASE_SCRIPTS[case_id]
    n = rerun_count_for(script["cls"])
    # A representative mixed/uniform rerun pattern sized to the real N for
    # this class (flaky->10 mixed, dependency/regression/env->3 all fail,
    # lint->0, Reproducer skips so this list is never even consumed).
    if script["cls"] == "flaky":
        reruns = [_tr(p) for p in [True, True, False, True, True, False, True, True, False, True][:n]]
    else:
        reruns = [_tr(False) for _ in range(n)]

    llm = _llm_for(script["cls"])
    sandbox = FakeSandbox(ci_result=_tr(False, script["ci_log"]), rerun_results=reruns)
    settings = Settings(_env_file=None)

    events = await _run_with_fakes(db, bus, settings, case_id, "normal", llm, sandbox)
    assert_contract_invariants(events)

    done = next(e for e in events if e["type"] == "done")
    assert done["outcome"] != "error", f"{case_id} errored: {events}"
    assert done["outcome"] in ("escalated", "reported", "budget_exhausted")

    # construction_kwargs still flows through to the no_creds/egress_off rows.
    guardrails = {g["rail"]: g for g in events if g["type"] == "guardrail"}
    assert guardrails["no_creds"]["fired"] is False
    assert guardrails["egress_off"]["fired"] is False


async def test_0128_tight_budget_exhausts(db, bus):
    # docs/05 §9 expected shape: "0128 tight | R(budget hit after 2 reruns)
    # | 2 model calls | 3 sandbox runs | budget_exhausted". The real tight
    # tool_calls cap (3) exhausts after watcher's 1 call + 2 reruns, right
    # before a 3rd run_test would fire -- the FakeSandbox's own over-call
    # guard backs this up if the graph's budget logic ever regresses.
    llm = _llm_for("env")
    sandbox = FakeSandbox(
        ci_result=_tr(False, CASE_SCRIPTS["0128"]["ci_log"]),
        rerun_results=[_tr(False), _tr(False)],
    )
    settings = Settings(_env_file=None)

    events = await _run_with_fakes(db, bus, settings, "0128", "tight", llm, sandbox)
    assert_contract_invariants(events)

    done = next(e for e in events if e["type"] == "done")
    assert done["outcome"] == "budget_exhausted"
    assert sandbox.run_test_calls == 2
    assert sandbox.run_ci_calls == 1

    # Reporter's own model call is exempt from the cap -- it still ran.
    assert ReportOutput in llm.calls


def test_case_config_never_carries_ground_truth_cls():
    # Invariant 7 (docs/04): ground-truth cls is never read by graph code.
    # CaseConfig (what nodes receive via state["config"]) structurally has
    # no `cls` field at all -- only FailureCase (API/scoreboard-only) does.
    assert "cls" not in CaseConfig.__dataclass_fields__
