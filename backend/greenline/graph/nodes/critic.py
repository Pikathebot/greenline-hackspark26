"""Critic node (docs/05-BACKEND-SPEC.md §6, §9). 0-3 model calls.

Deterministic-first: a red patch (or a guardrail miss) rejects with ZERO
LLM calls (docs/02-DECISIONS.md lesson: "if the sandbox is red: deterministic
reject, no LLM calls"). Only a fully green, within-cap, unprotected diff
goes to k-sample self-consistency voting (k=3 for a model diff, k=1 for a
tool diff).
"""

from __future__ import annotations

from greenline.events.models import CheckResult
from greenline.graph.budget import check_budget, guarded_node
from greenline.graph.state import GreenlineState
from greenline.guardrails.rails import diff_within_cap, protected_file
from greenline.llm.prompt_loader import load_prompt
from greenline.llm.schemas import CriticOutput

NODE = "critic"
SYSTEM_PROMPT = load_prompt("critic")


def _user_prompt(state: GreenlineState, attempt: dict) -> str:
    return (
        f"Diagnosis: {state.get('verdict_cls')}. Rationale: {state.get('rationale', '')}\n\n"
        f"Diff for {attempt['file']}:\n{attempt['diff']}\n\n"
        "Deterministic checks (tests and lint) are both green. Approve or reject."
    )


async def critic_node(state: GreenlineState) -> GreenlineState:
    emitter = state["emitter"]
    llm = state["llm"]
    attempt = state["patch_attempts"][-1]
    n = attempt["n"]

    async with guarded_node(state, NODE):
        deterministic = [
            CheckResult(name="tests_green", passed=bool(attempt.get("tests_passed"))),
            CheckResult(name="lint_green", passed=bool(attempt.get("lint_passed"))),
            CheckResult(name="diff_within_cap", passed=diff_within_cap(attempt["diff"])),
            CheckResult(name="no_protected_paths", passed=not protected_file([attempt["file"]])),
        ]

        if not all(c.passed for c in deterministic):
            emitter.narrate(NODE, "Deterministic checks failed -- rejecting without a model call")
            approved = False
            emitter.emit("critic.vote", n=n, samples=[], deterministic=deterministic, approved=approved)
            state["critic_votes"].append(
                {
                    "n": n,
                    "samples": [],
                    "deterministic": [c.model_dump() for c in deterministic],
                    "approved": approved,
                    "rationale": "deterministic checks failed",
                }
            )
        else:
            k = 3 if attempt["source"] == "model" else 1
            emitter.narrate(NODE, f"Taking {k} self-consistency sample{'s' if k != 1 else ''} at temperature 0.4")
            samples: list[str] = []
            rationale = ""
            for _ in range(k):
                check_budget(state)
                result = await llm.complete(SYSTEM_PROMPT, _user_prompt(state, attempt), CriticOutput, 0.4)
                emitter.record_model_call()
                samples.append(result.decision)
                rationale = result.rationale

            approve_count = sum(1 for s in samples if s == "approve")
            approved = approve_count > k / 2
            emitter.emit("critic.vote", n=n, samples=samples, deterministic=deterministic, approved=approved)
            state["critic_votes"].append(
                {
                    "n": n,
                    "samples": samples,
                    "deterministic": [c.model_dump() for c in deterministic],
                    "approved": approved,
                    "rationale": rationale,
                }
            )

        state["critic_approved"] = approved

    return state
