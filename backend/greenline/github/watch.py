"""B18: turn a red GitHub Actions run on the test repo into a Greenline case and start a live run.

Polls `GET /actions/runs?status=failure`. For each new failed run on a non-main, non-fix/
branch it fetches the branch into the local fixture repo, registers an "extra" case
(greenline.graph.cases / B17: branch, failing test node id, patch target, the REAL CI log as the
fallback log; nothing about outcomes, hard rule 4) and starts a live run.
"""

from __future__ import annotations

import asyncio
import logging
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from greenline.config import Settings
from greenline.graph.cases import (
    BUILTIN_CASE_IDS,
    load_extra_case_entries,
    reload_extra_cases,
    save_extra_case_entries,
)
from greenline.graph.nodes._util import failing_lines, parse_failing_nodeid
from greenline.graph.run import RunConflict, RunManager

log = logging.getLogger(__name__)

FIRST_GITHUB_CASE = 7001
_CLS_TAG = re.compile(r"\[cls:(flaky|dependency|regression|lint|env)\]")


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-c", "core.autocrlf=false", *args],
        cwd=repo, capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


class GitHubWatcher:
    def __init__(self, settings: Settings, run_manager: RunManager, client) -> None:
        self._settings = settings
        self._runs = run_manager
        self._client = client
        self._repo = settings.fixture_repo_path()
        self._extra_path = settings.extra_cases_path()
        self._seen: set[int] = set()
        self._pending: list[str] = []
        # Runs that were already red before we started are history, not news.
        self._since = datetime.now(timezone.utc)

    # -- loop ----------------------------------------------------------

    async def run(self) -> None:
        log.info("GitHub watcher on %s every %.0fs", self._settings.github_repo, self._settings.github_poll_s)
        while True:
            try:
                await self.poll_once()
            except asyncio.CancelledError:
                raise
            except Exception:  # noqa: BLE001 - the loop must survive anything
                log.exception("GitHub poll failed")
            await asyncio.sleep(self._settings.github_poll_s)

    async def poll_once(self) -> list[str]:
        """One tick. Returns the case ids registered this tick (for tests)."""
        created: list[str] = []
        runs = await asyncio.to_thread(self._client.failed_runs)
        for run in sorted(runs, key=lambda r: r["id"]):
            if run["id"] in self._seen or not self._is_new(run):
                continue
            self._seen.add(run["id"])
            try:
                case_id = await self._register(run)
            except Exception:  # noqa: BLE001
                log.exception("could not register GitHub run %s", run.get("id"))
                continue
            if case_id:
                created.append(case_id)
                self._pending.append(case_id)
        await self._start_pending()
        return created

    def _is_new(self, run: dict) -> bool:
        branch = run.get("head_branch") or ""
        if branch in ("main", "master") or branch.startswith("fix/"):
            return False
        created = datetime.fromisoformat(run["created_at"].replace("Z", "+00:00"))
        return created >= self._since

    # -- registering a case --------------------------------------------

    async def _register(self, run: dict) -> str | None:
        branch = run["head_branch"]
        log_text = await asyncio.to_thread(self._client.failed_job_log, run["id"])
        await asyncio.to_thread(_git, self._repo, "fetch", "origin", f"+{branch}:{branch}")
        changed = (await asyncio.to_thread(
            _git, self._repo, "diff", "--name-only", f"main...{branch}"
        )).split()

        message = ((run.get("head_commit") or {}).get("message") or branch).strip()
        tag = _CLS_TAG.search(message)
        entry_fields = {
            "branch": branch,
            "title": _CLS_TAG.sub("", message.splitlines()[0]).strip() or branch,
            "cls": tag.group(1) if tag else "regression",
            "failingTestNodeid": parse_failing_nodeid(log_text),
            "patchTarget": next((f for f in changed if not f.startswith("tests/")), None),
            "fallbackCiLog": failing_lines(log_text),
            "ciRunUrl": run.get("html_url"),
            "detectedAt": run["created_at"],
            "beat": "Detected from a red GitHub Actions run",
        }

        entries = load_extra_case_entries(self._extra_path)
        existing = next((e for e in entries if e["branch"] == branch), None)
        if existing is not None:  # same branch pushed again: refresh the case, don't add a new one
            existing.update(entry_fields)
            case_id = existing["id"]
        else:
            used = [int(e["id"]) for e in entries if e["id"].isdigit()]
            case_id = f"{max([FIRST_GITHUB_CASE - 1, *used]) + 1:04d}"
            assert case_id not in BUILTIN_CASE_IDS
            entries.append({"id": case_id, **entry_fields})
        save_extra_case_entries(self._extra_path, entries)
        reload_extra_cases(self._extra_path)
        log.info("GitHub run %s on %s -> case #%s", run["id"], branch, case_id)
        return case_id

    # -- starting runs (one at a time: one GPU) -------------------------

    async def _start_pending(self) -> None:
        while self._pending:
            try:
                run_id = await self._runs.start_run(self._pending[0], "live", "normal")
            except RunConflict:
                return  # a run is active; try again next tick
            except Exception:  # noqa: BLE001 - e.g. the case file changed under us
                log.exception("could not start case #%s", self._pending[0])
                self._pending.pop(0)
                continue
            log.info("started run %s for case #%s", run_id, self._pending[0])
            self._pending.pop(0)
