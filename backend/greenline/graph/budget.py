"""Budget enforcement (docs/05-BACKEND-SPEC.md §9).

Call check_budget(state) before each model or tool call; it raises when the
next call would exceed a cap, or elapsed time is at or above the cap. Every
node wraps its body in `guarded_node`, which catches BudgetExhausted, sets
state['budget_exhausted']=True, and still balances node.enter/exit so the
graph's conditional edges (which all check that flag first) can route
straight to the reporter.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from greenline.events.models import NodeId
from greenline.graph.state import GreenlineState


class BudgetExhausted(Exception):
    """Raised by check_budget(); caught by guarded_node, never propagates."""


def check_budget(state: GreenlineState) -> None:
    emitter = state["emitter"]
    caps = state["caps"]
    if emitter.model_calls >= caps.model_calls:
        raise BudgetExhausted(f"model_calls cap reached ({caps.model_calls})")
    if emitter.tool_calls >= caps.tool_calls:
        raise BudgetExhausted(f"tool_calls cap reached ({caps.tool_calls})")
    if emitter.elapsed_ms >= caps.elapsed_ms:
        raise BudgetExhausted(f"elapsed_ms cap reached ({caps.elapsed_ms})")


@asynccontextmanager
async def guarded_node(state: GreenlineState, node: NodeId) -> AsyncIterator[None]:
    emitter = state["emitter"]
    emitter.enter(node)
    try:
        yield
    except BudgetExhausted as exc:
        state["budget_exhausted"] = True
        emitter.log(node, "warn", f"budget exhausted: {exc}")
        emitter.exit(node, "fail", note=str(exc))
    except Exception as exc:
        # Balance the graph's enter/exit invariant even on a real failure,
        # then re-raise so the run manager's error handling takes over.
        emitter.exit(node, "fail", note=str(exc)[:200])
        raise
    else:
        emitter.exit(node, "ok")
