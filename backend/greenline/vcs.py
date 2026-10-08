"""Draft-PR integration (docs/05-BACKEND-SPEC.md §9 Reporter; D13).

Default is the dry-run path: a fake number and URL, flagged dry_run. B18 adds an opt-in
real path for cases detected from the GitHub test repo: push `fix/<caseId>` and open a
DRAFT PR into the broken branch (never main/master). It runs only when the Reporter hands
in a `RealPr` (DRY_RUN=false, GitHub configured, case branch exists on origin).
"""

from __future__ import annotations

import os
import random
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from greenline.guardrails.rails import is_main_or_master

_GIT_ENV = ["-c", "core.autocrlf=false", "-c", "core.eol=lf",
            "-c", "user.name=Greenline", "-c", "user.email=greenline@local"]


@dataclass
class RealPr:
    client: object  # greenline.github.client.GitHubClient (duck-typed for tests)
    repo_path: Path  # the local fixture repo (has `origin` = the GitHub test repo)
    base_branch: str  # the broken branch the PR targets
    file: str  # repo-relative path of the patched file
    content: str  # the Critic-approved new content of that file


def _git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    result = subprocess.run(
        ["git", *_GIT_ENV, *args], cwd=repo, capture_output=True, text=True,
        env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
    )
    if check and result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stdout}{result.stderr}".strip())
    return result


def branch_on_origin(repo: Path, branch: str) -> bool:
    """True if `branch` exists on the fixture repo's `origin` (i.e. a GitHub-detected case)."""
    result = _git(repo, "ls-remote", "--heads", "origin", branch, check=False)
    return result.returncode == 0 and bool(result.stdout.strip())


def _push_fix_branch(real: RealPr, head: str, title: str) -> None:
    """Commit the approved file on a temp worktree of the broken branch and push `head`.
    The fixture repo's own working tree and checked-out branch are never touched."""
    work = Path(tempfile.mkdtemp(prefix="greenline-pr-"))
    try:
        _git(real.repo_path, "worktree", "add", "-B", head, str(work), real.base_branch)
        target = work / real.file
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(real.content, encoding="utf-8", newline="\n")
        _git(work, "add", real.file)
        _git(work, "commit", "-m", title)
        _git(work, "push", "--force", "origin", f"{head}:{head}")
    finally:
        _git(real.repo_path, "worktree", "remove", "--force", str(work), check=False)
        shutil.rmtree(work, ignore_errors=True)
        _git(real.repo_path, "branch", "-D", head, check=False)


def open_draft_pr(
    title: str, body: str, branch: str, dry_run: bool = True, real: RealPr | None = None
) -> dict:
    if dry_run or real is None:
        number = random.randint(100, 999)
        return {
            "number": number,
            "url": f"https://github.com/acme/ledger-core/pull/{number}",
            "dry_run": True,
            "branch": branch,
        }

    # Hard rule 7, enforced here as well as by the no_main_write guardrail.
    if not branch.startswith("fix/") or is_main_or_master(branch):
        raise ValueError(f"refusing to push {branch!r}: PR heads must be fix/<caseId>")
    if is_main_or_master(real.base_branch):
        raise ValueError(f"refusing to open a PR into {real.base_branch!r}")

    _push_fix_branch(real, branch, title)
    pr = real.client.create_draft_pr(head=branch, base=real.base_branch, title=title, body=body)
    return {"number": pr["number"], "url": pr["url"], "dry_run": False, "branch": branch}
