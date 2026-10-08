"""Reproducer node (docs/05-BACKEND-SPEC.md §9). 0 model calls, N tool calls.

N by triage class: flaky 10, dependency/regression/env 3, lint 0. Skipped
(enter then exit(status='skip')) for lint, or for a warm memory hit
(Triage already found a similar past trace above threshold).
"""

from __future__ import annotations

import asyncio

from greenline.graph.budget import check_budget, guarded_node
from greenline.graph.cases import rerun_count_for
from greenline.graph.state import GreenlineState
from greenline.sandbox.runner import TestResult

NODE = "reproducer"


async def reproducer_node(state: GreenlineState) -> GreenlineState:
    emitter = state["emitter"]
    sandbox = state["sandbox"]
    config = state["config"]
    cls = state["triage_cls"]

    n = rerun_count_for(cls)
    memory_hit = state.get("memory_hit")
    if n == 0 or memory_hit is not None:
        note = (
            f"warm memory hit on #{memory_hit['case_id']}"
            if memory_hit is not None
            else "static analysis, nothing to rerun"
        )
        emitter.enter(NODE)
        emitter.exit(NODE, "skip", note=note)
        state["reruns"] = []
        state["reproducer_skipped"] = True
        return state

    async with guarded_node(state, NODE):
        check_budget(state)
        emitter.narrate(NODE, f"Re-running the failing test {n}x in fresh containers")

        reruns: list[TestResult] = []
        state["reruns"] = reruns  # same list object: visible even if exhausted mid-loop
        state["reproducer_skipped"] = False
        for i in range(1, n + 1):
            check_budget(state)
            result = await asyncio.to_thread(sandbox.run_test, config.branch, config.failing_test_nodeid)
            emitter.record_tool_call()
            emitter.emit("rerun.tick", n=i, total=n, passed=result.passed, duration_ms=result.duration_ms)
            reruns.append(result)

        passed = sum(1 for r in reruns if r.passed)
        failed = n - passed
        emitter.evidence(NODE, "observation", f"{passed} pass / {failed} fail across {n} isolated reruns")

    return state
