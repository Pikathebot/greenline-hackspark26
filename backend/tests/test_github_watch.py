"""B18: GitHub Actions polling and the real draft-PR path. No network: a fake client and
temp git repos (a bare "origin" plus the fixture clone)."""

from __future__ import annotations

import asyncio
import json
import subprocess
from pathlib import Path

import pytest

from greenline.config import Settings
from greenline.github.client import clean_log
from greenline.github.watch import GitHubWatcher
from greenline.graph.cases import FAILURE_CASES, reload_extra_cases
from greenline.vcs import RealPr, branch_on_origin, open_draft_pr

IDENT = ["-c", "user.name=t", "-c", "user.email=t@t", "-c", "core.autocrlf=false"]
LOG = (
    "2026-10-08T13:00:00.1234567Z collected 3 items\n"
    "2026-10-08T13:00:01.1234567Z FAILED tests/test_fees.py::test_fee - assert 103.0 == 97.0\n"
)


def git(cwd: Path, *args: str) -> str:
    result = subprocess.run(["git", *IDENT, *args], cwd=cwd, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    return result.stdout


@pytest.fixture
def repos(tmp_path):
    origin = tmp_path / "origin.git"
    origin.mkdir()
    git(origin, "init", "--bare", "-b", "main")
    work = tmp_path / "ledger-core"
    work.mkdir()
    git(work, "init", "-b", "main")
    (work / "ledger_core").mkdir()
    (work / "ledger_core" / "fees.py").write_text("def fee():\n    return 1\n", newline="\n")
    git(work, "add", "-A")
    git(work, "commit", "-m", "seed")
    git(work, "remote", "add", "origin", str(origin))
    git(work, "push", "origin", "main")
    # the "developer" pushes a broken branch straight to GitHub
    git(work, "checkout", "-b", "fee-bug")
    (work / "ledger_core" / "fees.py").write_text("def fee():\n    return -1\n", newline="\n")
    (work / "tests").mkdir()
    (work / "tests" / "test_fees.py").write_text("def test_fee():\n    pass\n", newline="\n")
    git(work, "add", "-A")
    git(work, "commit", "-m", "break fees [cls:dependency]")
    git(work, "push", "origin", "fee-bug")
    git(work, "checkout", "main")
    git(work, "branch", "-D", "fee-bug")  # GitHub has it; the fixture repo does not (yet)
    return work


class FakeClient:
    def __init__(self, runs):
        self.runs = runs
        self.prs = []

    def failed_runs(self):
        return self.runs

    def failed_job_log(self, run_id):
        return clean_log(LOG)

    def create_draft_pr(self, head, base, title, body):
        self.prs.append({"head": head, "base": base, "title": title})
        return {"number": 7, "url": "https://github.com/x/y/pull/7"}


class FakeRuns:
    def __init__(self):
        self.started = []

    async def start_run(self, case_id, mode, budget):
        self.started.append((case_id, mode, budget))
        return f"run-{case_id}"


def _run(run_id, branch="fee-bug", created="2999-01-01T00:00:00Z", **extra):
    return {
        "id": run_id,
        "head_branch": branch,
        "created_at": created,
        "html_url": f"https://github.com/x/y/actions/runs/{run_id}",
        "head_commit": {"message": "break fees [cls:dependency]\n\nbody"},
        **extra,
    }


def _watcher(repos, client, runs):
    settings = Settings(fixture_repo=str(repos), github_repo="x/y", GITHUB_TOKEN="t")
    return GitHubWatcher(settings, runs, client), settings


@pytest.fixture(autouse=True)
def _restore_builtins():
    yield
    reload_extra_cases(Path("does-not-exist.json"))


def test_failed_run_becomes_a_case_and_starts_a_run(repos):
    runs = FakeRuns()
    watcher, settings = _watcher(repos, FakeClient([_run(1)]), runs)
    created = asyncio.run(watcher.poll_once())

    assert created == ["7001"]
    assert runs.started == [("7001", "live", "normal")]
    case = FAILURE_CASES["7001"]
    assert case.branch == "fee-bug"
    assert case.cls == "dependency"
    assert case.title == "break fees"
    assert case.ci_run_url == "https://github.com/x/y/actions/runs/1"
    entry = json.loads(settings.extra_cases_path().read_text())[0]
    assert entry["failingTestNodeid"] == "tests/test_fees.py::test_fee"
    assert entry["patchTarget"] == "ledger_core/fees.py"
    assert "FAILED tests/test_fees.py::test_fee" in entry["fallbackCiLog"]
    assert "2026-10-08" not in entry["fallbackCiLog"]  # Actions timestamps stripped
    git(repos, "rev-parse", "--verify", "fee-bug")  # the branch was fetched locally


def test_main_fix_old_and_repeated_runs_are_ignored(repos):
    runs = FakeRuns()
    client = FakeClient([
        _run(1, branch="main"),
        _run(2, branch="fix/7001"),
        _run(3, created="2000-01-01T00:00:00Z"),  # red before the backend started
        _run(4),
    ])
    watcher, _ = _watcher(repos, client, runs)
    assert asyncio.run(watcher.poll_once()) == ["7001"]
    assert asyncio.run(watcher.poll_once()) == []  # run 4 already seen
    assert len(runs.started) == 1


def test_same_branch_pushed_again_reuses_the_case(repos):
    runs = FakeRuns()
    client = FakeClient([_run(1)])
    watcher, _ = _watcher(repos, client, runs)
    asyncio.run(watcher.poll_once())
    client.runs = [_run(1), _run(2)]
    assert asyncio.run(watcher.poll_once()) == ["7001"]
    assert [r[0] for r in runs.started] == ["7001", "7001"]
    assert [c for c in FAILURE_CASES if c.startswith("7")] == ["7001"]


def test_run_waits_while_another_run_is_active(repos):
    from greenline.graph.run import RunConflict

    class Busy(FakeRuns):
        busy = True

        async def start_run(self, case_id, mode, budget):
            if self.busy:
                raise RunConflict("run-x")
            return await super().start_run(case_id, mode, budget)

    runs = Busy()
    watcher, _ = _watcher(repos, FakeClient([_run(1)]), runs)
    asyncio.run(watcher.poll_once())
    assert runs.started == []
    runs.busy = False
    asyncio.run(watcher.poll_once())
    assert runs.started == [("7001", "live", "normal")]


def test_real_pr_pushes_fix_branch_and_opens_draft_pr_into_the_broken_branch(repos, tmp_path):
    client = FakeClient([])
    git(repos, "fetch", "origin", "+fee-bug:fee-bug")
    assert branch_on_origin(repos, "fee-bug")
    assert not branch_on_origin(repos, "case/0142-flaky-settlement")

    real = RealPr(client, repos, "fee-bug", "ledger_core/fees.py", "def fee():\n    return 1\n")
    pr = open_draft_pr("Fix fee", "body", "fix/7001", dry_run=False, real=real)

    assert pr == {"number": 7, "url": "https://github.com/x/y/pull/7", "dry_run": False,
                  "branch": "fix/7001"}
    assert client.prs == [{"head": "fix/7001", "base": "fee-bug", "title": "Fix fee"}]
    origin = tmp_path / "origin.git"
    assert git(origin, "show", "fix/7001:ledger_core/fees.py") == "def fee():\n    return 1\n"
    assert git(origin, "rev-parse", "main") == git(repos, "rev-parse", "main")  # main untouched
    assert git(repos, "branch", "--show-current").strip() == "main"
    assert git(repos, "status", "--porcelain").strip() == ""
    assert "fix/7001" not in git(repos, "branch", "--list")  # temp branch cleaned up


def test_real_pr_refuses_main_and_non_fix_heads(repos):
    client = FakeClient([])
    real = RealPr(client, repos, "main", "ledger_core/fees.py", "x\n")
    with pytest.raises(ValueError):
        open_draft_pr("t", "b", "fix/7001", dry_run=False, real=real)
    real = RealPr(client, repos, "fee-bug", "ledger_core/fees.py", "x\n")
    for head in ("main", "feature/x"):
        with pytest.raises(ValueError):
            open_draft_pr("t", "b", head, dry_run=False, real=real)
    assert client.prs == []


def test_dry_run_is_unchanged():
    pr = open_draft_pr("t", "b", "fix/0139")
    assert pr["dry_run"] is True and pr["branch"] == "fix/0139"
    # DRY_RUN=false without a RealPr (local-only case) still simulates, honestly flagged
    assert open_draft_pr("t", "b", "fix/0139", dry_run=False)["dry_run"] is True


def test_clean_log_strips_timestamps_and_colours():
    raw = "2026-10-08T13:00:01.1234567Z \x1b[31mFAILED\x1b[0m tests/a.py::t\n"
    assert clean_log(raw) == "FAILED tests/a.py::t"
