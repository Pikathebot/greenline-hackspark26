"""Triage node (docs/05-BACKEND-SPEC.md §9). 1 model call.

Memory: embed "{test name}: {rationale}", query top-3, drop hits from the
same case_id, keep similarity >= 0.82 AND hit.cls == triage.cls. Emits
memory.hit for the best (first, since candidates are similarity-sorted)
qualifying hit. Embedding/memory errors are swallowed -- memory is an
optimisation, never a hard dependency. If state carries no embed/
memory_store (e.g. the fake-driven termination tests), memory is simply
skipped, same as a real lookup failure.
"""

from __future__ import annotations

import asyncio

from greenline.graph.budget import check_budget, guarded_node
from greenline.graph.nodes._util import test_name_for
from greenline.graph.state import GreenlineState
from greenline.llm.prompt_loader import load_prompt
from greenline.llm.schemas import TriageOutput
from greenline.memory.store import SIMILARITY_THRESHOLD

NODE = "triage"
SYSTEM_PROMPT = load_prompt("triage")


def _user_prompt(ci_log: str) -> str:
    return f"CI log (most recent lines):\n{ci_log}\n\nClassify this failure."


async def _lookup_memory_hit(state: GreenlineState, cls: str, rationale: str) -> dict | None:
    embed = state.get("embed")
    memory_store = state.get("memory_store")
    if embed is None or memory_store is None:
        return None

    try:
        query_text = f"{test_name_for(state['config'])}: {rationale}"
        vector = await embed.embed(query_text)
        candidates = await asyncio.to_thread(memory_store.query_top_k, vector)
    except Exception:
        return None  # embedding/memory errors are swallowed (optimisation only)

    case_id = state["case_id"]
    for candidate in candidates:
        if candidate["case_id"] == case_id:
            continue  # drop hits from the same case_id
        if candidate["similarity"] >= SIMILARITY_THRESHOLD and candidate["cls"] == cls:
            return candidate  # candidates are similarity-sorted: first match is best
    return None


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

        memory_hit = await _lookup_memory_hit(state, result.cls, result.rationale)
        state["memory_hit"] = memory_hit
        if memory_hit:
            emitter.emit(
                "memory.hit",
                case_ref=memory_hit["case_id"],
                similarity=memory_hit["similarity"],
                summary=memory_hit["summary"],
            )

    return state
