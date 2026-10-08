"""The contract. Mirrors docs/04-EVENT-CONTRACT.md exactly.

Frozen after gate G0: additive changes only (new optional field or new
variant), in both languages in the same commit, announced to the partner.
Never rename, never remove.
"""

from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter
from pydantic.alias_generators import to_camel

# ---------------------------------------------------------------------------
# Shared enums (Literals)
# ---------------------------------------------------------------------------

NodeId = Literal[
    "watcher", "triage", "reproducer", "analyst", "patcher", "critic", "reporter"
]
FailureClass = Literal["flaky", "dependency", "env", "lint", "regression"]
RailId = Literal["protected_file", "diff_cap", "no_main_write", "no_creds", "egress_off"]
RunMode = Literal["live", "demo"]
BudgetPreset = Literal["normal", "tight"]
Outcome = Literal["reported", "escalated", "budget_exhausted", "error"]
NodeExitStatus = Literal["ok", "skip", "fail"]
LogLevel = Literal["info", "warn", "error"]
EvidenceKind = Literal["command", "observation", "citation"]
PatchSource = Literal["model", "tool"]
PatchResult = Literal["green", "red", "vetoed"]
CriticSample = Literal["approve", "reject"]
ReportKind = Literal["pr", "escalation"]


class CamelModel(BaseModel):
    """Base for every wire model: camelCase JSON, snake_case Python."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


# ---------------------------------------------------------------------------
# Shared value objects
# ---------------------------------------------------------------------------


class CheckResult(CamelModel):
    name: str
    passed: bool
    detail: str | None = None


class BudgetCaps(CamelModel):
    model_calls: int
    tool_calls: int
    elapsed_ms: int


# ---------------------------------------------------------------------------
# GreenlineEvent variants (discriminated union on `type`)
# ---------------------------------------------------------------------------


class _EventBase(CamelModel):
    t: int


class RunStartEvent(_EventBase):
    type: Literal["run.start"] = "run.start"
    run_id: str
    case_id: str
    mode: RunMode
    model: str
    budget_preset: BudgetPreset
    caps: BudgetCaps


class NodeEnterEvent(_EventBase):
    type: Literal["node.enter"] = "node.enter"
    node: NodeId


class NodeExitEvent(_EventBase):
    type: Literal["node.exit"] = "node.exit"
    node: NodeId
    duration_ms: int
    status: NodeExitStatus
    note: str | None = None


class LogEvent(_EventBase):
    type: Literal["log"] = "log"
    node: NodeId
    level: LogLevel
    text: str


class EvidenceEvent(_EventBase):
    type: Literal["evidence"] = "evidence"
    node: NodeId
    kind: EvidenceKind
    text: str
    ref: str | None = None


class RerunTickEvent(_EventBase):
    type: Literal["rerun.tick"] = "rerun.tick"
    n: int
    total: int
    passed: bool
    duration_ms: int


class MemoryHitEvent(_EventBase):
    type: Literal["memory.hit"] = "memory.hit"
    case_ref: str
    similarity: float
    summary: str


class VerdictEvent(_EventBase):
    type: Literal["verdict"] = "verdict"
    cls: FailureClass
    confidence: float
    rationale: str


class PatchAttemptEvent(_EventBase):
    type: Literal["patch.attempt"] = "patch.attempt"
    n: int
    file: str
    diff: str
    source: PatchSource
    result: PatchResult


class CriticVoteEvent(_EventBase):
    type: Literal["critic.vote"] = "critic.vote"
    n: int
    samples: list[CriticSample]
    deterministic: list[CheckResult]
    approved: bool


class BudgetEvent(_EventBase):
    type: Literal["budget"] = "budget"
    model_calls: int
    tool_calls: int
    elapsed_ms: int


class GuardrailEvent(_EventBase):
    type: Literal["guardrail"] = "guardrail"
    rail: RailId
    fired: bool
    note: str


class ReportEvent(_EventBase):
    type: Literal["report"] = "report"
    kind: ReportKind
    title: str
    body: str
    pr_url: str | None = None
    dry_run: bool | None = None


class ErrorEvent(_EventBase):
    type: Literal["error"] = "error"
    node: NodeId | None = None
    message: str


class DoneEvent(_EventBase):
    type: Literal["done"] = "done"
    outcome: Outcome


GreenlineEvent = Annotated[
    Union[
        RunStartEvent,
        NodeEnterEvent,
        NodeExitEvent,
        LogEvent,
        EvidenceEvent,
        RerunTickEvent,
        MemoryHitEvent,
        VerdictEvent,
        PatchAttemptEvent,
        CriticVoteEvent,
        BudgetEvent,
        GuardrailEvent,
        ReportEvent,
        ErrorEvent,
        DoneEvent,
    ],
    Field(discriminator="type"),
]

EventAdapter: TypeAdapter[GreenlineEvent] = TypeAdapter(GreenlineEvent)


def dump_event(event: BaseModel) -> dict:
    """Wire representation: camelCase keys, optional-absent fields omitted."""
    return event.model_dump(by_alias=True, exclude_none=True, mode="json")


def parse_event(payload: dict) -> GreenlineEvent:
    return EventAdapter.validate_python(payload)


# ---------------------------------------------------------------------------
# FailureCase (static case metadata) and case/run summaries
# ---------------------------------------------------------------------------


class FailureCase(CamelModel):
    id: str
    title: str
    repo: str
    branch: str
    cls: FailureClass  # ground truth; used ONLY by the scoreboard, never by the graph
    detected_at: str  # ISO timestamp, display only
    ci_run_url: str  # cosmetic
    beat: str  # one line: what this case demonstrates


class RunSummary(CamelModel):
    run_id: str
    outcome: Outcome
    duration_ms: int
    model_calls: int
    tool_calls: int
    mode: RunMode


class CaseSummary(FailureCase):
    last_run: RunSummary | None = None  # last completed LIVE run of this case
    has_demo_run: bool  # demo_runs/<id>.json exists -> "Recorded" mode is available
