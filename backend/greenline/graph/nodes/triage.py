"""Triage node (docs/05-BACKEND-SPEC.md §9). 1 model call.

Memory (embedding + sqlite-vec lookup) lands at ticket B10 -- until then
state['memory_hit'] is always None and Reproducer never skips on it.
"""

from __future__ import annotations

from greenline.graph.budget import check_budget, guarded_node
from greenline.graph.state import GreenlineState
from greenline.llm.prompt_loader import load_prompt
from greenline.llm.schemas import TriageOutput

NODE = "triage"
SYSTEM_PROMPT = load_prompt("triage")


def _user_prompt(ci_log: str) -> str:
    return f"CI log (most recent lines):\n{ci_log}\n\nClassify this failure."


async def triage_node(state: GreenlineState) -> GreenlineState:
    emitter = state["emitter"]
    llm = state["llm"]

    async with guarded_node(state, NODE):
        check_budget(state)
        emitter.narrate(NODE, "Classifying the failure against the five known classes")

        result = await llm.complete(SYSTEM_PROMPT, _user_prompt(state["ci_log"]), TriageOutput, 0.3)
        emitter.record_model_call()
        emitter.evidence(NODE, "citation", result.rationale)

        state["triage_cls"] = result.cls
        state["memory_hit"] = None  # populated at ticket B10

    return state
