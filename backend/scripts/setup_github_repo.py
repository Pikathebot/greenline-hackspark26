"""B18: one-time setup of the GitHub test repo (docs/plans/B18-github-ci.md).

Adds .github/workflows/ci.yml to the LOCAL fixture repo's main, and with --create makes
the public GitHub repo (via your `gh` login) and pushes `main` to it. Only `main` is
pushed: the six case branches stay local. Safe to re-run.

Run from backend/: .venv\\Scripts\\python.exe scripts\\setup_github_repo.py --create
Then: create a fine-grained PAT for that repo only (Contents RW, Pull requests RW,
Actions read) and put in backend\\.env:
    GITHUB_TOKEN=...
    GREENLINE_GITHUB_REPO=Pikathebot/ledger-core
    GREENLINE_DRY_RUN=false
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from greenline.config import get_settings

WORKFLOW = """name: CI
on:
  push:
  pull_request:
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install pytest ruff
      - name: Test and lint (same two commands as Greenline's sandbox)
        shell: bash {0}
        run: |
          pytest -q; ec1=$?
          ruff check .; ec2=$?
          [ $ec1 -eq 0 ] && [ $ec2 -eq 0 ]
"""

IDENT = ["-c", "user.name=Greenline Seed", "-c", "user.email=seed@local",
         "-c", "core.autocrlf=false", "-c", "core.eol=lf"]


def run(cmd: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess:
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if check and result.returncode != 0:
        sys.exit(f"{' '.join(cmd)} failed:\n{result.stdout}{result.stderr}")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default="Pikathebot/ledger-core")
    parser.add_argument("--create", action="store_true", help="create the public GitHub repo and push main")
    args = parser.parse_args()

    repo = get_settings().fixture_repo_path()
    if not (repo / ".git").exists():
        sys.exit(f"fixture repo not seeded at {repo} (run scripts/seed_repo.py)")
    git = lambda *a, **k: run(["git", *IDENT, *a], cwd=repo, **k)  # noqa: E731

    if git("branch", "--show-current").stdout.strip() != "main" or git("status", "--porcelain").stdout.strip():
        sys.exit("fixture repo must be on a clean main")

    workflow = repo / ".github" / "workflows" / "ci.yml"
    if not workflow.exists() or workflow.read_text(encoding="utf-8") != WORKFLOW:
        workflow.parent.mkdir(parents=True, exist_ok=True)
        workflow.write_text(WORKFLOW, encoding="utf-8", newline="\n")
        git("add", ".github/workflows/ci.yml")
        git("commit", "-m", "ci: GitHub Actions workflow (pytest + ruff)")
        print("Committed the CI workflow to the fixture repo's main.")
    else:
        print("CI workflow already on main.")

    url = f"https://github.com/{args.repo}.git"
    remotes = git("remote").stdout.split()
    if "origin" not in remotes:
        git("remote", "add", "origin", url)
    elif git("remote", "get-url", "origin").stdout.strip() != url:
        sys.exit(f"origin already points elsewhere: {git('remote', 'get-url', 'origin').stdout.strip()}")

    exists = run(["gh", "repo", "view", args.repo], check=False).returncode == 0
    if not exists:
        if not args.create:
            print(f"{args.repo} does not exist yet. Re-run with --create to make it (public) and push main.")
            return
        run(["gh", "repo", "create", args.repo, "--public",
             "--description", "Throwaway test repo for Greenline (HackSpark'26)"])
        print(f"Created {args.repo}.")

    git("push", "origin", "main")
    print(f"Pushed main to {url}. Open https://github.com/{args.repo}/actions to see CI run.")
    print("Next: create a fine-grained PAT for this repo only and set GITHUB_TOKEN, "
          "GREENLINE_GITHUB_REPO, GREENLINE_DRY_RUN=false in backend\\.env.")


if __name__ == "__main__":
    main()
