"""Run manager (docs/05-BACKEND-SPEC.md §4). One active run at a time.

Every run ends in exactly one `done`, whatever happens: the task is wrapped
in try/except Exception -> error event -> done{outcome:'error'}, finally
always updates the `runs` row and closes the bus.

A live run builds the graph (watcher -> triage -> reproducer -> analyst ->
reporter; Patcher/Critic land at ticket B9) and invokes it with a fresh
GreenlineState. Any node's exception propagates up to this module's own
try/except, which turns it into `error` + `done{outcome:'error'}`.
"""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import Callable
from datetime import UTC, datetime

from greenline.config import Settings
from greenline.events.bus import EventBus
from greenline.events.emitter import RunEmitter
from greenline.graph.build import build_graph
from greenline.graph.cases import CASE_CONFIGS, FAILURE_CASES
from greenline.llm.client import LLMClient, get_llm_client
from greenline.persistence.db import Database
from greenline.sandbox.runner import SandboxRunner


class RunNotFound(Exception):
    """Unknown case id."""


class RunConflict(Exception):
    """A run is already active (one GPU, one run at a time)."""

    def __init__(self, active_run_id: str):
        self.active_run_id = active_run_id
        super().__init__(active_run_id)


class DemoRunMissing(Exception):
    """mode='demo' requested but demo_runs/<case_id>.json does not exist."""


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


class RunManager:
    def __init__(
        self,
        db: Database,
        bus: EventBus,
        settings: Settings,
        *,
        sandbox_factory: Callable[[], SandboxRunner] | None = None,
        llm_factory: Callable[[], LLMClient] | None = None,
    ) -> None:
        self._db = db
        self._bus = bus
        self._settings = settings
        self._active_run_id: str | None = None
        self._active_case_id: str | None = None
        self._lock = asyncio.Lock()
        self._graph = build_graph()  # stateless topology, compiled once and reused
        # Overridable for tests (B8: fake sandbox/LLM, real everything else).
        self._sandbox_factory = sandbox_factory or (
            lambda: SandboxRunner(settings.fixture_repo_path(), settings.sandbox_image)
        )
        self._llm_factory = llm_factory or get_llm_client

    @property
    def active(self) -> tuple[str, str] | None:
        if self._active_run_id is None:
            return None
        return self._active_run_id, self._active_case_id

    async def start_run(self, case_id: str, mode: str, budget_preset: str) -> str:
        if case_id not in FAILURE_CASES:
            raise RunNotFound(case_id)
        if mode == "demo":
            demo_path = self._settings.demo_runs_path() / f"{case_id}.json"
            if not demo_path.exists():
                raise DemoRunMissing(case_id)

        async with self._lock:
            if self._active_run_id is not None:
                raise RunConflict(self._active_run_id)
            run_id = f"run-{case_id}-{uuid.uuid4().hex[:8]}"
            self._db.insert_run(run_id, case_id, mode, budget_preset, _now_iso())
            self._active_run_id = run_id
            self._active_case_id = case_id

        asyncio.create_task(self._execute(run_id, case_id, mode, budget_preset))
        return run_id

    async def _execute(self, run_id: str, case_id: str, mode: str, budget_preset: str) -> None:
        emitter = RunEmitter(run_id, self._db, self._bus)
        outcome = "error"
        try:
            if mode == "demo":
                from greenline.demo.player import play_demo_run

                outcome = await play_demo_run(emitter, case_id, self._settings)
            else:
                outcome = await self._run_live(emitter, case_id, budget_preset)
        except Exception as exc:  # noqa: BLE001 - every run ends in exactly one done
            emitter.emit("error", message=str(exc) or exc.__class__.__name__)
            outcome = "error"
            # The Reporter's template fallback is optional for `error` (invariant 6);
            # the Reporter itself lands at ticket B9.
        finally:
            # Demo playback re-emits the recording's own done event (it's
            # "every stored event except run.start"), so don't double-emit.
            if not emitter.done_emitted:
                emitter.emit("done", outcome=outcome)
            self._db.finish_run(
                run_id,
                status="error" if outcome == "error" else "complete",
                outcome=outcome,
                ended_at=_now_iso(),
                model_calls=emitter.model_calls,
                tool_calls=emitter.tool_calls,
                duration_ms=emitter.elapsed_ms,
            )
            self._bus.close(run_id)
            async with self._lock:
                if self._active_run_id == run_id:
                    self._active_run_id = None
                    self._active_case_id = None

    async def _run_live(self, emitter: RunEmitter, case_id: str, budget_preset: str) -> str:
        caps = self._settings.caps(budget_preset)
        emitter.start(case_id, "live", self._settings.model, budget_preset, caps)

        sandbox = self._sandbox_factory()
        kwargs = sandbox.construction_kwargs()
        # Asserted from the sandbox's real construction kwargs, not hardcoded.
        emitter.emit(
            "guardrail",
            rail="no_creds",
            fired=bool(kwargs["environment"]),
            note=f"sandbox environment={kwargs['environment']!r}",
        )
        emitter.emit(
            "guardrail",
            rail="egress_off",
            fired=not kwargs["network_disabled"],
            note=f"sandbox network_disabled={kwargs['network_disabled']}",
        )

        initial_state = {
            "emitter": emitter,
            "sandbox": sandbox,
            "llm": self._llm_factory(),
            "caps": caps,
            "case_id": case_id,
            "config": CASE_CONFIGS[case_id],
            "budget_exhausted": False,
            "patch_attempts": [],
            "critic_votes": [],
            "critic_approved": False,
            "dry_run": self._settings.dry_run,
        }
        final_state = await self._graph.ainvoke(initial_state)
        return final_state["outcome"]
