"""B8/B9 (docs/05-BACKEND-SPEC.md §12.5): "the most valuable test". Runs the
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
from greenline.llm.schemas import AnalystOutput, CriticOutput, PatchOutput, ReportOutput, TriageOutput
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
    """Stands in for SandboxRunner: scripted run_ci/run_test/run_patched
    results, a small read-only file map, and a scripted breaking diff."""

    def __init__(
        self,
        ci_result: TestResult,
        rerun_results: list[TestResult],
        files: dict[str, str] | None = None,
        breaking_diff_text: str = "",
        patch_results: list[dict] | None = None,
        ruff_fix_result: TestResult | None = None,
    ) -> None:
        self._ci_result = ci_result
        self._rerun_results = list(rerun_results)
        self._files = files or {}
        self._breaking_diff_text = breaking_diff_text
        self._patch_results = list(patch_results) if patch_results is not None else []
        self._ruff_fix_result = ruff_fix_result
        self.run_ci_calls = 0
        self.run_test_calls = 0
        self.run_patched_calls = 0
        self.ruff_fix_calls = 0

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

    def read_file(self, branch: str, path: str) -> str:
        if path not in self._files:
            raise FileNotFoundError(f"{branch}:{path}")
        return self._files[path]

    def breaking_diff(self, branch: str) -> str:
        return self._breaking_diff_text

    def ruff_fix(self, branch: str, path: str) -> TestResult:
        self.ruff_fix_calls += 1
        if self._ruff_fix_result is not None:
            return self._ruff_fix_result
        return _tr(True, self._files.get(path, ""))

    def run_patched(self, branch: str, path: str, content: str) -> dict:
        self.run_patched_calls += 1
        if not self._patch_results:
            raise AssertionError(
                f"run_patched called more times ({self.run_patched_calls}) than scripted"
            )
        return self._patch_results.pop(0)

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


def _llm_for(cls: str, extra: dict[type, object] | None = None) -> FakeLLM:
    responses = {
        TriageOutput: TriageOutput(cls=cls, rationale="fake triage rationale"),
        AnalystOutput: AnalystOutput(cls=cls, rationale="fake analyst rationale", evidence_strength="strong"),
        ReportOutput: ReportOutput(title="fake title", body="fake body"),
    }
    if extra:
        responses.update(extra)
    return FakeLLM(responses)


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

# Patcher-reaching cases (0139, 0137, 0131) need extra fake-sandbox fixtures.
# 0142/0144 (protected_file) and 0128 (no_safe_fix) never reach Patcher, so
# they need nothing extra.
_RETRY_SOURCE = "from ledger_core.vendor.http_util import Retry\n\n\ndef make_retry_policy():\n    return Retry(total=3)\n"
_RETRY_POLICY_SOURCE = "from ledger_core.vendor.http_util import RetryPolicy\n\n\ndef make_retry_policy():\n    return RetryPolicy(total=3)\n"
_ROLLUP_REGRESSED = "def in_window(txn_date, start, end):\n    return start <= txn_date <= end\n"
_ROLLUP_FIXED = "def in_window(txn_date, start, end):\n    return start <= txn_date < end\n"
_ROUTES_WITH_UNUSED_IMPORT = "import os\nimport json\n"
_ROUTES_FIXED = "import os\n"

PATCHER_EXTRAS: dict[str, dict] = {
    "0139": dict(
        files={
            "ledger_core/http_client.py": _RETRY_SOURCE,
            "tests/test_http_client.py": "def test_make_retry_policy_returns_retry():\n    pass\n",
        },
        llm_extra={PatchOutput: PatchOutput(new_content=_RETRY_POLICY_SOURCE, summary="rename Retry -> RetryPolicy")},
        patch_results=[{"tests_passed": True, "lint_passed": True, "output": "ok"}],
    ),
    "0137": dict(
        files={
            "ledger_core/rollup.py": _ROLLUP_REGRESSED,
            "tests/test_rollup.py": "def test_reconcile_window_boundary():\n    pass\n",
        },
        llm_extra={PatchOutput: PatchOutput(new_content=_ROLLUP_FIXED, summary="flip <= back to <")},
        # Exercises the critic loop "for free": attempt 1 is red (deterministic
        # reject, 0 model calls) -> loops back to Patcher -> attempt 2 is green
        # -> k=3 LLM sampling approves (docs/05 §9's own "critic loop is
        # acceptable" shape for #0137).
        patch_results=[
            {"tests_passed": False, "lint_passed": True, "output": "still red"},
            {"tests_passed": True, "lint_passed": True, "output": "now green"},
        ],
    ),
    "0131": dict(
        files={"ledger_core/routes.py": _ROUTES_WITH_UNUSED_IMPORT},
        llm_extra=None,  # tool path (ruff_fix), no model call for the patch itself
        patch_results=[{"tests_passed": True, "lint_passed": True, "output": "ok"}],
        ruff_fix_result=_tr(True, _ROUTES_FIXED),
    ),
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

    extra = PATCHER_EXTRAS.get(case_id, {})
    llm = _llm_for(script["cls"], extra=extra.get("llm_extra"))
    # Every case always needs a CriticOutput response available, even
    # when this particular case doesn't reach the model-sampling branch.
    llm._responses.setdefault(CriticOutput, CriticOutput(decision="approve", rationale="fake critic rationale"))

    sandbox = FakeSandbox(
        ci_result=_tr(False, script["ci_log"]),
        rerun_results=reruns,
        files=extra.get("files"),
        patch_results=extra.get("patch_results"),
        ruff_fix_result=extra.get("ruff_fix_result"),
    )
    settings = Settings(_env_file=None)

    events = await _run_with_fakes(db, bus, settings, case_id, "normal", llm, sandbox)
    assert_contract_invariants(events)

    done = next(e for e in events if e["type"] == "done")
    assert done["outcome"] != "error", f"{case_id} errored: {events}"
    assert done["outcome"] in ("escalated", "reported", "budget_exhausted")

    if case_id in PATCHER_EXTRAS:
        # These three are expected to actually get patched and approved.
        assert done["outcome"] == "reported", f"{case_id}: {events}"
        reports = [e for e in events if e["type"] == "report"]
        assert reports[0]["kind"] == "pr"
        assert reports[0]["dryRun"] is True
        assert "prUrl" in reports[0]

    # construction_kwargs still flows through to the no_creds/egress_off rows.
    guardrails = {g["rail"]: g for g in events if g["type"] == "guardrail"}
    assert guardrails["no_creds"]["fired"] is False
    assert guardrails["egress_off"]["fired"] is False


async def test_0137_exercises_the_critic_loop(db, bus):
    # Same script as the parametrized case above, but explicitly checking
    # the loop actually happened: 2 patch attempts, first rejected
    # deterministically (0 model calls for that vote), second approved.
    extra = PATCHER_EXTRAS["0137"]
    llm = _llm_for("regression", extra=extra["llm_extra"])
    llm._responses[CriticOutput] = CriticOutput(decision="approve", rationale="fake critic rationale")
    sandbox = FakeSandbox(
        ci_result=_tr(False, CASE_SCRIPTS["0137"]["ci_log"]),
        rerun_results=[_tr(False), _tr(False), _tr(False)],
        files=extra["files"],
        patch_results=list(extra["patch_results"]),
    )
    settings = Settings(_env_file=None)

    events = await _run_with_fakes(db, bus, settings, "0137", "normal", llm, sandbox)
    assert_contract_invariants(events)

    patch_attempts = [e for e in events if e["type"] == "patch.attempt"]
    assert [a["n"] for a in patch_attempts] == [1, 2]
    assert patch_attempts[0]["result"] == "red"
    assert patch_attempts[1]["result"] == "green"

    critic_votes = [e for e in events if e["type"] == "critic.vote"]
    assert [v["n"] for v in critic_votes] == [1, 2]
    assert critic_votes[0]["samples"] == []  # deterministic reject, no LLM calls
    assert critic_votes[0]["approved"] is False
    assert len(critic_votes[1]["samples"]) == 3  # k=3 for a model-sourced diff
    assert critic_votes[1]["approved"] is True

    done = next(e for e in events if e["type"] == "done")
    assert done["outcome"] == "reported"


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


# -- B11: budget exhaustion mid-Patcher / mid-Critic -----------------------
#
# Neither the normal nor the tight preset's real numbers ever reach this
# far before running out of tool_calls in Reproducer first (confirmed live
# in test_graph.py: both 0128-tight and 0139-tight exhaust there). So the
# check_budget() call sites inside patcher.py and critic.py -- same
# function, same guarded_node pattern as every other node, but never
# actually triggered by a raise anywhere else in this suite -- get custom
# caps here instead of the normal/tight presets, specifically to make sure
# they abort into budget_exhausted rather than attempting a call anyway.


def _0139_fakes():
    extra = PATCHER_EXTRAS["0139"]
    llm = _llm_for("dependency", extra=extra["llm_extra"])
    llm._responses.setdefault(CriticOutput, CriticOutput(decision="approve", rationale="fake"))
    sandbox = FakeSandbox(
        ci_result=_tr(False, CASE_SCRIPTS["0139"]["ci_log"]),
        rerun_results=[_tr(False), _tr(False), _tr(False)],
        files=extra["files"],
        patch_results=list(extra["patch_results"]),
    )
    return llm, sandbox


async def test_tight_model_calls_exhausts_at_patcher_entry(db, bus):
    # Just enough model budget for triage + analyst (2); Patcher's own
    # check_budget() at entry must abort before attempting the model call.
    settings = Settings(_env_file=None, tight_model_calls=2, tight_tool_calls=16, tight_elapsed_ms=180_000)
    llm, sandbox = _0139_fakes()

    events = await _run_with_fakes(db, bus, settings, "0139", "tight", llm, sandbox)
    assert_contract_invariants(events)

    done = next(e for e in events if e["type"] == "done")
    assert done["outcome"] == "budget_exhausted"
    assert [e for e in events if e["type"] == "patch.attempt"] == []
    assert PatchOutput not in llm.calls


async def test_tight_model_calls_exhausts_inside_critic_sampling(db, bus):
    # check_budget() conservatively re-checks ALL three counters before
    # every call, including a pure tool call -- so cap=3 would stop
    # Patcher itself right before run_patched (model_calls already at 3
    # from Patcher's own call). cap=4 gives Patcher's full attempt (model
    # + tool) room to complete, so Critic's first k-sample call_budget()
    # is the one that aborts, after 1 of its k=3 samples.
    settings = Settings(_env_file=None, tight_model_calls=4, tight_tool_calls=16, tight_elapsed_ms=180_000)
    llm, sandbox = _0139_fakes()

    events = await _run_with_fakes(db, bus, settings, "0139", "tight", llm, sandbox)
    assert_contract_invariants(events)

    done = next(e for e in events if e["type"] == "done")
    assert done["outcome"] == "budget_exhausted"
    patch_attempts = [e for e in events if e["type"] == "patch.attempt"]
    assert len(patch_attempts) == 1  # Patcher's full attempt (model + tool) completed
    # Critic started sampling (consumed its one allowed call) but never
    # finished k=3, so it never reached its own emit("critic.vote", ...).
    assert [e for e in events if e["type"] == "critic.vote"] == []
