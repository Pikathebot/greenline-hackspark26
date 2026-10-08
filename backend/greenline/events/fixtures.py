"""One valid instance of every GreenlineEvent variant.

Shared by tests/test_contract.py (round-trip assertions) and
scripts/export_variants.py (the JSON handed to Person A). This is test data,
not demo data — it never feeds a real run.
"""

from __future__ import annotations

from greenline.events.models import (
    BudgetCaps,
    BudgetEvent,
    CheckResult,
    CriticVoteEvent,
    DoneEvent,
    ErrorEvent,
    EvidenceEvent,
    GuardrailEvent,
    LogEvent,
    MemoryHitEvent,
    NodeEnterEvent,
    NodeExitEvent,
    PatchAttemptEvent,
    RerunTickEvent,
    ReportEvent,
    RunStartEvent,
    VerdictEvent,
)

# One instance per variant, optional fields populated where they exist.
ALL_VARIANTS: dict[str, object] = {
    "run.start": RunStartEvent(
        t=0,
        run_id="run-0142-abc",
        case_id="0142",
        mode="live",
        model="qwen3-8b",
        budget_preset="normal",
        caps=BudgetCaps(model_calls=16, tool_calls=16, elapsed_ms=180_000),
    ),
    "node.enter": NodeEnterEvent(t=120, node="watcher"),
    "node.exit": NodeExitEvent(
        t=1800, node="watcher", duration_ms=1680, status="ok", note="warm memory hit on #0142"
    ),
    "log": LogEvent(t=150, node="watcher", level="info", text="Pulling the red build"),
    "evidence": EvidenceEvent(
        t=1600, node="watcher", kind="command", text="pytest -q && ruff check .", ref="#0142"
    ),
    "rerun.tick": RerunTickEvent(t=5400, n=4, total=10, passed=False, duration_ms=1830),
    "memory.hit": MemoryHitEvent(
        t=2100, case_ref="0142", similarity=0.91, summary="flaky settlement reconciliation"
    ),
    "verdict": VerdictEvent(
        t=9000, cls="flaky", confidence=0.86, rationale="7 pass / 3 fail across 10 reruns"
    ),
    "patch.attempt": PatchAttemptEvent(
        t=11000,
        n=1,
        file="tests/test_settlement.py",
        diff="--- a/x\n+++ b/x\n",
        source="model",
        result="green",
    ),
    "critic.vote": CriticVoteEvent(
        t=12500,
        n=1,
        samples=["approve", "approve", "reject"],
        deterministic=[CheckResult(name="tests_green", passed=True, detail="10/10")],
        approved=True,
    ),
    "budget": BudgetEvent(t=9100, model_calls=3, tool_calls=11, elapsed_ms=9100),
    "guardrail": GuardrailEvent(
        t=9200, rail="protected_file", fired=True, note="tests/** is protected"
    ),
    "report": ReportEvent(
        t=15000,
        kind="pr",
        title="Fix flaky settlement reconciliation",
        body="Draft PR body.",
        pr_url="https://github.com/acme/ledger-core/pull/42",
        dry_run=True,
    ),
    "error": ErrorEvent(t=200, node="watcher", message="model server unreachable"),
    "done": DoneEvent(t=15200, outcome="reported"),
}
