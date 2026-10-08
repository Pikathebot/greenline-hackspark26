"""GreenlineState (docs/05-BACKEND-SPEC.md §9). A TypedDict carrying live
objects (emitter, sandbox, llm, caps) plus data fields. No LangGraph
checkpointer -- our persistence is the event log."""

from __future__ import annotations

from pathlib import Path
from typing import TypedDict

from greenline.events.emitter import RunEmitter
from greenline.events.models import BudgetCaps, FailureClass
from greenline.graph.cases import CaseConfig
from greenline.llm.client import LLMClient
from greenline.memory.embed import EmbedClient
from greenline.memory.store import MemoryStore
from greenline.sandbox.runner import SandboxRunner, TestResult


class GreenlineState(TypedDict, total=False):
    # live objects
    emitter: RunEmitter
    sandbox: SandboxRunner
    llm: LLMClient
    caps: BudgetCaps
    embed: EmbedClient  # absent in the fake-driven termination tests -> memory just skips
    memory_store: MemoryStore

    # static case config
    case_id: str
    config: CaseConfig

    # watcher
    ci_log: str

    # triage
    triage_cls: FailureClass
    memory_hit: dict | None  # a qualifying MemoryStore hit, or None

    # reproducer
    reruns: list[TestResult]
    reproducer_skipped: bool

    # analyst
    verdict_cls: FailureClass
    confidence: float
    rationale: str
    blocked: bool
    block_reason: str | None  # 'no_safe_fix' | 'protected_file'

    # budget
    budget_exhausted: bool

    # patcher / critic (ticket B9)
    patch_attempts: list[dict]  # [{n, file, diff, source, result}]
    critic_votes: list[dict]  # [{n, samples, deterministic, approved}]
    critic_approved: bool

    # reporter
    dry_run: bool
    github_client: object | None  # B18: GitHubClient when configured, else None
    fixture_repo: Path  # B18: local fixture repo (for the real-PR push)
    outcome: str
