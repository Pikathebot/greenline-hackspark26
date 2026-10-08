"""Watcher node (docs/05-BACKEND-SPEC.md §9). 0 model calls, 1+ tool calls.

A sandboxed CI run can come back clean even on a genuinely flaky case
(by design: ~30% failure per process for #0142/#0144) -- a clean log gives
Triage nothing to classify. Watcher retries up to MAX_ATTEMPTS times until
it actually reproduces the reported failure, uniformly for every case
(this isn't case-specific: any case could in principle show this). If it
still can't reproduce after retrying, it says so explicitly rather than
silently handing Triage a misleading clean log.
"""

from __future__ import annotations

import asyncio

from greenline.graph.budget import check_budget, guarded_node
from greenline.graph.nodes._util import first_failing_line, last_n_lines
from greenline.graph.state import GreenlineState
from greenline.sandbox.runner import TestResult

NODE = "watcher"
MAX_ATTEMPTS = 3


async def watcher_node(state: GreenlineState) -> GreenlineState:
    emitter = state["emitter"]
    sandbox = state["sandbox"]
    config = state["config"]

    async with guarded_node(state, NODE):
        check_budget(state)
        emitter.narrate(NODE, "Pulling the red build and re-running CI in a sealed sandbox")

        result: TestResult | None = None
        infra_failure: Exception | None = None

        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                result = await asyncio.to_thread(sandbox.run_ci, config.branch)
                emitter.record_tool_call()
            except Exception as exc:
                infra_failure = exc
                result = None
                break

            if not result.passed:
                break  # reproduced the reported failure

            if attempt < MAX_ATTEMPTS:
                emitter.log(
                    NODE,
                    "info",
                    f"sandbox re-run came back green (attempt {attempt}/{MAX_ATTEMPTS}); "
                    "retrying to try to reproduce the reported failure",
                )
                check_budget(state)

        if result is None:
            emitter.log(
                NODE, "warn", f"sandbox CI run failed for infrastructure reasons ({infra_failure}); using cached CI log"
            )
            raw_log = config.fallback_ci_log
        else:
            emitter.evidence(NODE, "command", "pytest -q && ruff check .")
            raw_log = result.stdout + result.stderr
            if result.passed:
                raw_log = (
                    f"NOTE: {MAX_ATTEMPTS} sandboxed re-runs all came back green, "
                    "despite this build being reported red. Consistent with an "
                    "intermittent/flaky failure.\n\n" + raw_log
                )
                emitter.log(
                    NODE,
                    "warn",
                    f"could not reproduce a failure after {MAX_ATTEMPTS} attempts -- "
                    "proceeding to Triage with that noted explicitly",
                )

        ci_log = last_n_lines(raw_log, 60)
        emitter.evidence(NODE, "observation", first_failing_line(raw_log))
        state["ci_log"] = ci_log

    return state
