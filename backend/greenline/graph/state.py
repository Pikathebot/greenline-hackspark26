"""GreenlineState (docs/05-BACKEND-SPEC.md §9). A TypedDict carrying live
objects (emitter, sandbox, llm, caps) plus data fields. No LangGraph
checkpointer -- our persistence is the event log."""

from __future__ import annotations

from typing import TypedDict

from greenline.events.emitter import RunEmitter
from greenline.events.models import BudgetCaps, FailureClass
from greenline.graph.cases import CaseConfig
from greenline.llm.client import LLMClient
from greenline.sandbox.runner import SandboxRunner, TestResult


class GreenlineState(TypedDict, total=False):
    # live objects
    emitter: RunEmitter
    sandbox: SandboxRunner
    llm: LLMClient
    caps: BudgetCaps

    # static case config
    case_id: str
    config: CaseConfig

    # watcher
    ci_log: str

    # triage
    triage_cls: FailureClass
    memory_hit: dict | None  # populated at ticket B10; always None until then

    # reproducer
    reruns: list[TestResult]
    reproducer_skipped: bool

    # analyst
    verdict_cls: FailureClass
    confidence: float
    rationale: str
    blocked: bool
    block_reason: str | None  # 'no_safe_fix' | 'protected_file' | 'no_patcher_yet' (until B9)

    # budget
    budget_exhausted: bool

    # reporter
    outcome: str
