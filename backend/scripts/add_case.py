"""B17: add a failure case to the running app, no restart (docs/plans/B17-live-case.md).

    new <id> --slug <s>                       branch off main in the fixture repo; then break something
    finish <id> --title T --cls C [--beat B]  commit, run CI in the sandbox, register the case
    from-patch <id> --slug S --patch FILE --title T --cls C   new + git apply + finish
    list | remove <id>

The server re-reads backend/fixtures/extra_cases.json on every /api/cases call, so after
`finish` just press F5 in the UI. Extra cases never count toward the scoreboard.

Run from backend/: .venv\\Scripts\\python.exe scripts\\add_case.py new 0151 --slug window
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from greenline.config import get_settings
from greenline.graph.cases import (
    BUILTIN_CASE_IDS,
    load_extra_case_entries,
    save_extra_case_entries,
)
from greenline.graph.nodes._util import failing_lines, first_failing_line, parse_failing_nodeid
from greenline.sandbox.runner import SandboxRunner

CLASSES = ["flaky", "dependency", "regression", "lint", "env"]
GIT_ENV = ["-c", "core.autocrlf=false", "-c", "core.eol=lf"]
IDENT = ["-c", "user.name=Greenline Case", "-c", "user.email=case@local"]


def git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    result = subprocess.run(
        ["git", *GIT_ENV, *IDENT, *args], cwd=repo, capture_output=True, text=True
    )
    if check and result.returncode != 0:
        sys.exit(f"git {' '.join(args)} failed:\n{result.stdout}{result.stderr}")
    return result


def fail(message: str) -> None:
    sys.exit(f"error: {message}")


def cmd_new(repo: Path, case_id: str, slug: str) -> str:
    if case_id in BUILTIN_CASE_IDS:
        fail(f"{case_id} is a built-in case")
    if not re.fullmatch(r"\d{4}", case_id):
        fail("case id must be four digits")
    if not re.fullmatch(r"[a-z0-9-]+", slug):
        fail("slug may only contain a-z, 0-9 and '-'")
    settings = get_settings()
    if any(e["id"] == case_id for e in load_extra_case_entries(settings.extra_cases_path())):
        fail(f"{case_id} already exists (use `remove {case_id}` first)")
    if git(repo, "status", "--porcelain").stdout.strip():
        fail(f"fixture repo {repo} has uncommitted changes; clean it first")
    branch = f"case/{case_id}-{slug}"
    if git(repo, "rev-parse", "--verify", branch, check=False).returncode == 0:
        fail(f"branch {branch} already exists")
    git(repo, "checkout", "main")
    git(repo, "checkout", "-b", branch)
    print(f"On branch {branch}. Break something under:\n  {repo}")
    print(f"Then: add_case.py finish {case_id} --title \"...\" --cls <{'|'.join(CLASSES)}>")
    return branch


def cmd_finish(repo: Path, case_id: str, title: str, cls: str, beat: str) -> None:
    branch = git(repo, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    if not branch.startswith(f"case/{case_id}-"):
        fail(f"current branch is {branch!r}, expected case/{case_id}-*")
    git(repo, "add", "-A")
    if git(repo, "status", "--porcelain").stdout.strip():
        git(repo, "commit", "-m", f"case {case_id}: {title}")
    elif git(repo, "rev-list", "--count", f"main..{branch}").stdout.strip() == "0":
        fail("no changes on this branch: break something first")

    settings = get_settings()
    result = SandboxRunner(settings.fixture_repo_path(), settings.sandbox_image).run_ci(branch)
    if result.passed:
        print("CI is green, nothing to triage. Break something and run finish again.")
        sys.exit(1)

    output = result.stdout + result.stderr
    changed = git(repo, "diff", "--name-only", f"main...{branch}").stdout.split()
    patch_target = next((f for f in changed if not f.startswith("tests/")), None)
    entry = {
        "id": case_id,
        "branch": branch,
        "title": title,
        "cls": cls,
        "failingTestNodeid": parse_failing_nodeid(output),
        "patchTarget": patch_target,
        "fallbackCiLog": failing_lines(output),
        "beat": beat,
        "detectedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    git(repo, "checkout", "main")
    path = settings.extra_cases_path()
    entries = [e for e in load_extra_case_entries(path) if e["id"] != case_id] + [entry]
    save_extra_case_entries(path, entries)

    print(f"CI red: {first_failing_line(output)}")
    print(f"  failing test : {entry['failingTestNodeid']}")
    print(f"  patch target : {entry['patchTarget']}")
    print(f"Added #{case_id}. Press F5 in the UI.")


def cmd_list() -> None:
    entries = load_extra_case_entries(get_settings().extra_cases_path())
    for e in entries:
        print(f"#{e['id']}  {e['cls']:<10} {e['branch']}  {e['title']}")
    if not entries:
        print("(no extra cases)")


def cmd_remove(repo: Path, case_id: str) -> None:
    path = get_settings().extra_cases_path()
    entries = load_extra_case_entries(path)
    match = [e for e in entries if e["id"] == case_id]
    if not match:
        fail(f"no extra case {case_id}")
    save_extra_case_entries(path, [e for e in entries if e["id"] != case_id])
    git(repo, "checkout", "main")
    git(repo, "branch", "-D", match[0]["branch"], check=False)
    print(f"Removed #{case_id}.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("new")
    p.add_argument("case_id")
    p.add_argument("--slug", required=True)

    for name in ("finish", "from-patch"):
        p = sub.add_parser(name)
        p.add_argument("case_id")
        p.add_argument("--title", required=True)
        p.add_argument("--cls", required=True, choices=CLASSES)
        p.add_argument("--beat", default="Added live")
        if name == "from-patch":
            p.add_argument("--slug", required=True)
            p.add_argument("--patch", required=True)

    sub.add_parser("list")
    p = sub.add_parser("remove")
    p.add_argument("case_id")

    args = parser.parse_args()
    repo = get_settings().fixture_repo_path()
    if args.command != "list" and not (repo / ".git").exists():
        fail(f"fixture repo not seeded at {repo} (run scripts/seed_repo.py)")

    if args.command == "new":
        cmd_new(repo, args.case_id, args.slug)
    elif args.command == "finish":
        cmd_finish(repo, args.case_id, args.title, args.cls, args.beat)
    elif args.command == "from-patch":
        patch = Path(args.patch).resolve()
        if not patch.exists():
            fail(f"patch file not found: {patch}")
        cmd_new(repo, args.case_id, args.slug)
        # --ignore-whitespace: the .diff may be checked out with CRLF on Windows.
        git(repo, "apply", "--ignore-whitespace", str(patch))
        cmd_finish(repo, args.case_id, args.title, args.cls, args.beat)
    elif args.command == "list":
        cmd_list()
    elif args.command == "remove":
        cmd_remove(repo, args.case_id)


if __name__ == "__main__":
    main()
