"""Reporter node (docs/05-BACKEND-SPEC.md §9). 1 model call, template
fallback. The Reporter must never fail, and its own model call is EXEMPT
from the budget cap -- "the report is always written", even after
budget_exhausted.
"""

from __future__ import annotations

from greenline.graph.state import GreenlineState
from greenline.llm.prompt_loader import load_prompt
from greenline.llm.schemas import ReportOutput

NODE = "reporter"
SYSTEM_PROMPT = load_prompt("reporter")

_BLOCK_REASON_TEXT = {
    "no_safe_fix": (
        "no safe automated fix exists for this failure class (env drift can't be "
        "patched without masking a deployment gap)"
    ),
    "protected_file": (
        "the only fix would touch a protected path, and Greenline never edits "
        "tests to make them pass"
    ),
    "no_patcher_yet": "an automated patch isn't available yet for this class of fix in this build",
}


def _determine_outcome(state: GreenlineState) -> str:
    if state.get("budget_exhausted"):
        return "budget_exhausted"
    # No Critic exists until ticket B9, so `reported` can't actually happen
    # yet; this is written so B9 only needs to set critic_approved on state.
    if state.get("critic_approved"):
        return "reported"
    return "escalated"


def _block_reason_text(state: GreenlineState) -> str:
    return _BLOCK_REASON_TEXT.get(
        state.get("block_reason"), "the run could not reach a safe automated fix"
    )


def _context_summary(state: GreenlineState, outcome: str) -> str:
    cls = state.get("verdict_cls") or state.get("triage_cls") or "unknown"
    rationale = state.get("rationale", "")

    if outcome == "budget_exhausted":
        return (
            f"The run exhausted its model/tool/time budget while investigating a "
            f"{cls} failure and must escalate rather than guess. "
            f"Partial evidence so far: {rationale or '(none yet)'}."
        )
    return (
        f"Verdict: {cls} (confidence {state.get('confidence', 0):.2f}). "
        f"Rationale: {rationale}. No patch was applied because "
        f"{_block_reason_text(state)}."
    )


def _template_report(state: GreenlineState, outcome: str) -> ReportOutput:
    cls = state.get("verdict_cls") or state.get("triage_cls") or "unknown"
    rationale = state.get("rationale", "")

    if outcome == "budget_exhausted":
        title = f"Escalation: budget exhausted investigating a {cls} failure"
        body = (
            f"Greenline ran out of its model/tool/time budget while investigating "
            f"this {cls} failure and is escalating rather than guessing. {rationale}"
        ).strip()
    else:
        title = f"Escalation: {cls} failure, no patch applied"
        body = (
            f"Verdict: {cls} (confidence {state.get('confidence', 0):.2f}). {rationale} "
            f"No patch was applied because {_block_reason_text(state)}. Escalating to "
            "a human with the evidence attached."
        ).strip()
    return ReportOutput(title=title, body=body)


async def reporter_node(state: GreenlineState) -> GreenlineState:
    emitter = state["emitter"]
    llm = state["llm"]

    emitter.enter(NODE)
    outcome = _determine_outcome(state)
    emitter.narrate(NODE, "Writing the final report")

    try:
        result = await llm.complete(
            SYSTEM_PROMPT, _context_summary(state, outcome), ReportOutput, 0.3
        )
        emitter.record_model_call()
    except Exception as exc:  # the Reporter must never fail
        emitter.log(NODE, "warn", f"model unavailable, using the template report: {exc}")
        result = _template_report(state, outcome)

    kind = "pr" if outcome == "reported" else "escalation"
    report_kwargs: dict = {"kind": kind, "title": result.title, "body": result.body}
    if kind == "pr":
        # Real dry-run PR open (vcs.open_draft_pr) lands with the Patcher/
        # Critic loop at ticket B9.
        report_kwargs["dry_run"] = True
    emitter.emit("report", **report_kwargs)

    state["outcome"] = outcome
    emitter.exit(NODE, "ok")
    return state
