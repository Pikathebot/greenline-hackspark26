"""Analyst node (docs/05-BACKEND-SPEC.md §9). 1 model call.

Guardrail: no safe target -> blocked (no_safe_fix). Otherwise check
protected_file on the patch target -> blocked (protected_file) if it
fires. If neither blocks, routes to the real Patcher/Critic loop.

Memory: stores a trace only if Reproducer actually ran (docs/02-DECISIONS
lesson 12 -- a warm-skipped run must not write its borrowed trace back).
Like Triage's lookup, this is swallowed on any failure and simply skipped
if state carries no embed/memory_store.
"""

from __future__ import annotations

import asyncio

from greenline.graph.budget import check_budget, guarded_node
from greenline.graph.confidence import confidence
from greenline.graph.nodes._util import test_name_for
from greenline.graph.state import GreenlineState
from greenline.guardrails.rails import protected_file
from greenline.llm.prompt_loader import load_prompt
from greenline.llm.schemas import AnalystOutput

NODE = "analyst"
SYSTEM_PROMPT = load_prompt("analyst")


def _evidence_summary(state: GreenlineState) -> str:
    if state["reproducer_skipped"]:
        if state.get("memory_hit") is not None:
            hit = state["memory_hit"]
            return f"Memory hit: {hit['summary']} (similarity {hit['similarity']:.2f})"
        return "lint: static analysis only"

    reruns = state["reruns"]
    n = len(reruns)
    passed = sum(1 for r in reruns if r.passed)
    failed = n - passed
    tail = next((r.stdout + r.stderr for r in reruns if not r.passed), "")
    tail = "\n".join(tail.splitlines()[-15:])
    return f"{passed} pass / {failed} fail across {n} isolated reruns.\nSample failure tail:\n{tail}"


def _user_prompt(state: GreenlineState) -> str:
    return (
        f"Triage classified this as: {state['triage_cls']}\n\n"
        f"CI log (most recent lines):\n{state['ci_log']}\n\n"
        f"Evidence:\n{_evidence_summary(state)}\n\n"
        "Confirm or revise the classification."
    )


async def _store_memory_trace(state: GreenlineState, cls: str, rationale: str) -> None:
    if state["reproducer_skipped"]:
        return  # a warm-skipped run must not write its borrowed trace back
    embed = state.get("embed")
    memory_store = state.get("memory_store")
    if embed is None or memory_store is None:
        return
    try:
        query_text = f"{test_name_for(state['config'])}: {rationale}"
        vector = await embed.embed(query_text)
        await asyncio.to_thread(
            memory_store.store, state["emitter"].run_id, state["case_id"], cls, rationale, vector
        )
    except Exception:
        pass  # memory is an optimisation, never a hard dependency


async def analyst_node(state: GreenlineState) -> GreenlineState:
    emitter = state["emitter"]
    llm = state["llm"]
    config = state["config"]

    async with guarded_node(state, NODE):
        check_budget(state)
        emitter.narrate(NODE, "Reading the evidence and computing confidence from it")

        result = await llm.complete(SYSTEM_PROMPT, _user_prompt(state), AnalystOutput, 0.3)
        emitter.record_model_call()

        conf = confidence(result.cls, state["reruns"], state.get("memory_hit"))
        emitter.emit("verdict", cls=result.cls, confidence=conf, rationale=result.rationale)
        emitter.evidence(NODE, "citation", result.rationale)

        state["verdict_cls"] = result.cls
        state["confidence"] = conf
        state["rationale"] = result.rationale

        await _store_memory_trace(state, result.cls, result.rationale)

        if config.patch_target is None:
            emitter.evidence(NODE, "observation", "no safe automated fix for env failures -- escalating")
            state["blocked"] = True
            state["block_reason"] = "no_safe_fix"
        else:
            fired = protected_file([config.patch_target])
            emitter.emit(
                "guardrail",
                rail="protected_file",
                fired=fired,
                note=(
                    f"{config.patch_target} matches tests/** -- escalating instead of patching"
                    if fired
                    else f"{config.patch_target} is not a protected path"
                ),
            )
            if fired:
                state["blocked"] = True
                state["block_reason"] = "protected_file"
            else:
                state["blocked"] = False

    return state
