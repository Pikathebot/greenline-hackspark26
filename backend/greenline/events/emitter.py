"""RunEmitter: the only place `t` is created (docs/05-BACKEND-SPEC.md §3,
docs/04-EVENT-CONTRACT.md invariant 2). Stamps, validates, persists, publishes.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable

from greenline.events.bus import EventBus
from greenline.events.models import (
    BudgetCaps,
    EvidenceKind,
    LogLevel,
    NodeExitStatus,
    NodeId,
    dump_event,
    parse_event,
)
from greenline.persistence.db import Database


class RunEmitter:
    """One instance per run. Not shared across runs."""

    def __init__(
        self,
        run_id: str,
        db: Database,
        bus: EventBus,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.run_id = run_id
        self._db = db
        self._bus = bus
        self._clock = clock
        self._start = clock()
        self._last_t = 0
        self._seq = 0
        self.model_calls = 0
        self.tool_calls = 0
        self._node_entered_at: dict[str, int] = {}

    def _elapsed_ms(self) -> int:
        return max(0, int((self._clock() - self._start) * 1000))

    @property
    def elapsed_ms(self) -> int:
        return self._elapsed_ms()

    def emit(self, type_: str, **fields) -> dict:
        """Stamps t = max(last_t, elapsed), validates, persists, publishes."""
        t = max(self._last_t, self._elapsed_ms())
        self._last_t = t
        payload = {"t": t, "type": type_, **fields}
        event = parse_event(payload)  # fails loudly on a malformed event
        wire = dump_event(event)
        seq = self._seq
        self._seq += 1
        self._db.insert_event(self.run_id, seq, t, type_, json.dumps(wire))
        self._bus.publish(self.run_id, {"seq": seq, "payload": wire})
        return wire

    # -- node lifecycle ----------------------------------------------------

    def enter(self, node: NodeId) -> dict:
        self._node_entered_at[node] = self._elapsed_ms()
        return self.emit("node.enter", node=node)

    def exit(self, node: NodeId, status: NodeExitStatus, note: str | None = None) -> dict:
        entered_at = self._node_entered_at.pop(node, self._elapsed_ms())
        duration_ms = max(0, self._elapsed_ms() - entered_at)
        kwargs: dict = {"node": node, "duration_ms": duration_ms, "status": status}
        if note is not None:
            kwargs["note"] = note
        return self.emit("node.exit", **kwargs)

    def narrate(self, node: NodeId, text: str) -> dict:
        return self.emit("log", node=node, level="info", text=text)

    def log(self, node: NodeId, level: LogLevel, text: str) -> dict:
        return self.emit("log", node=node, level=level, text=text)

    def evidence(self, node: NodeId, kind: EvidenceKind, text: str, ref: str | None = None) -> dict:
        kwargs: dict = {"node": node, "kind": kind, "text": text}
        if ref is not None:
            kwargs["ref"] = ref
        return self.emit("evidence", **kwargs)

    # -- budget --------------------------------------------------------

    def record_model_call(self) -> dict:
        self.model_calls += 1
        return self._emit_budget()

    def record_tool_call(self) -> dict:
        self.tool_calls += 1
        return self._emit_budget()

    def _emit_budget(self) -> dict:
        return self.emit(
            "budget",
            model_calls=self.model_calls,
            tool_calls=self.tool_calls,
            elapsed_ms=self._elapsed_ms(),
        )

    # -- run.start -------------------------------------------------------

    def start(self, case_id: str, mode: str, model: str, budget_preset: str, caps: BudgetCaps) -> dict:
        return self.emit(
            "run.start",
            run_id=self.run_id,
            case_id=case_id,
            mode=mode,
            model=model,
            budget_preset=budget_preset,
            caps=caps,
        )
