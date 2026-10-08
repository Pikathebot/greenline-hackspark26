"""B4: seeds backend/fixtures/ledger-core (docs/06-FIXTURE-REPO-SPEC.md).

A real, tiny Python package with pytest + ruff: a green `main` and six
`case/*` branches, each carrying one genuine defect. The sandbox runs real
tests against it, so every verdict is a consequence of real execution.

Idempotent: if all six case branches already exist, does nothing.
--force rebuilds from scratch. No network needed. Writes files with \n line
endings only (core.autocrlf/core.eol are forced off/lf on this repo so git
never rewrites them on add or checkout). Commits as "Greenline Seed <seed@local>".

Run from backend/: .venv\\Scripts\\python.exe scripts\\seed_repo.py [--force]
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_PATH = BACKEND_ROOT / "fixtures" / "ledger-core"

GIT_AUTHOR_ENV = {
    "GIT_AUTHOR_NAME": "Greenline Seed",
    "GIT_AUTHOR_EMAIL": "seed@local",
    "GIT_COMMITTER_NAME": "Greenline Seed",
    "GIT_COMMITTER_EMAIL": "seed@local",
}


def _git(*args: str, cwd: Path) -> subprocess.CompletedProcess:
    env = {**os.environ, **GIT_AUTHOR_ENV}
    result = subprocess.run(["git", *args], cwd=cwd, env=env, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed:\n{result.stdout}\n{result.stderr}")
    return result


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def _existing_branches(repo: Path) -> set[str]:
    if not (repo / ".git").exists():
        return set()
    result = subprocess.run(["git", "branch", "--list"], cwd=repo, capture_output=True, text=True)
    if result.returncode != 0:
        return set()
    return {line.strip().lstrip("* ").strip() for line in result.stdout.splitlines() if line.strip()}


# ---------------------------------------------------------------------------
# `main` branch file contents (docs/06-FIXTURE-REPO-SPEC.md § main)
# ---------------------------------------------------------------------------

PYPROJECT_TOML = """[tool.ruff]
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
"""

REQUIREMENTS_TXT = (
    "# No external runtime dependencies. See ledger_core/vendor/ for vendored stand-ins.\n"
)

SETTLEMENT_PY_MAIN = '''"""Settlement reconciliation for end-of-day ledger close."""


def reconcile_settlement(entries: list[dict], timeout: float = 0.5) -> bool:
    """True if the amounts net to zero (abs(sum) < 1e-6)."""
    total = sum(entry["amount"] for entry in entries)
    return abs(total) < 1e-6
'''

ROLLUP_PY_MAIN = '''"""Settlement window membership."""


def in_window(txn_date, start, end) -> bool:
    """True if txn_date falls within [start, end) -- end is exclusive."""
    return start <= txn_date < end
'''

ROUTES_PY_MAIN = '''"""Ledger summary routes."""

import os
from typing import Any


def get_ledger_summary(ledger_id: str) -> dict[str, Any]:
    return {
        "ledger_id": ledger_id,
        "status": "ok",
        "region": os.environ.get("LEDGER_REGION", "unset"),
    }
'''

VENDOR_HTTP_UTIL_MAIN = '''"""Vendored stand-in for a third-party HTTP retry library (no network needed)."""


class Retry:
    def __init__(self, total: int = 3):
        self.total = total
'''

HTTP_CLIENT_PY = '''"""Thin wrapper around the vendored retry policy."""

from ledger_core.vendor.http_util import Retry


def make_retry_policy() -> Retry:
    return Retry(total=3)
'''

TEST_ROLLUP_PY = '''from datetime import date

from ledger_core.rollup import in_window


def test_reconcile_window_boundary():
    start = date(2026, 9, 1)
    end = date(2026, 9, 8)
    assert in_window(date(2026, 9, 1), start, end) is True
    assert in_window(date(2026, 9, 7), start, end) is True
    assert in_window(date(2026, 9, 8), start, end) is False
'''

TEST_HTTP_CLIENT_PY = '''from ledger_core.http_client import make_retry_policy


def test_make_retry_policy_returns_retry():
    assert make_retry_policy().total == 3
'''

TEST_SETTLEMENT_PY = '''from ledger_core.settlement import reconcile_settlement


def test_settlement_reconciles_at_eod():
    entries = [{"amount": 100.0}, {"amount": -100.0}]
    assert reconcile_settlement(entries) is True
'''

GITIGNORE = "__pycache__/\n*.pyc\n.pytest_cache/\n.ruff_cache/\n"


def write_main_branch(repo: Path) -> None:
    _write(repo / "pyproject.toml", PYPROJECT_TOML)
    _write(repo / "requirements.txt", REQUIREMENTS_TXT)
    _write(repo / "ledger_core" / "__init__.py", "")
    _write(repo / "ledger_core" / "settlement.py", SETTLEMENT_PY_MAIN)
    _write(repo / "ledger_core" / "rollup.py", ROLLUP_PY_MAIN)
    _write(repo / "ledger_core" / "routes.py", ROUTES_PY_MAIN)
    _write(repo / "ledger_core" / "vendor" / "__init__.py", "")
    _write(repo / "ledger_core" / "vendor" / "http_util.py", VENDOR_HTTP_UTIL_MAIN)
    _write(repo / "ledger_core" / "http_client.py", HTTP_CLIENT_PY)
    _write(repo / "tests" / "__init__.py", "")
    _write(repo / "tests" / "test_rollup.py", TEST_ROLLUP_PY)
    _write(repo / "tests" / "test_http_client.py", TEST_HTTP_CLIENT_PY)
    _write(repo / "tests" / "test_settlement.py", TEST_SETTLEMENT_PY)
    _write(repo / ".gitignore", GITIGNORE)


def verify_main_green(repo: Path) -> None:
    pytest_result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"], cwd=repo, capture_output=True, text=True
    )
    if pytest_result.returncode != 0:
        raise RuntimeError(
            f"main branch is not green (pytest exit {pytest_result.returncode}):\n"
            f"{pytest_result.stdout}\n{pytest_result.stderr}"
        )
    ruff_result = subprocess.run(
        [sys.executable, "-m", "ruff", "check", "."], cwd=repo, capture_output=True, text=True
    )
    if ruff_result.returncode != 0:
        raise RuntimeError(
            f"main branch is not green (ruff exit {ruff_result.returncode}):\n"
            f"{ruff_result.stdout}\n{ruff_result.stderr}"
        )


# ---------------------------------------------------------------------------
# The six case branches (docs/06-FIXTURE-REPO-SPEC.md § The six branches)
# ---------------------------------------------------------------------------

SETTLEMENT_PY_0142 = '''"""Settlement reconciliation for end-of-day ledger close."""

import os


def reconcile_settlement(entries: list[dict], timeout: float = 0.5) -> bool:
    """True if the amounts net to zero (abs(sum) < 1e-6).

    Simulates load-dependent timeouts: about 30% of calls raise TimeoutError,
    standing in for real settlement latency under load.
    """
    if os.urandom(1)[0] < 77:
        raise TimeoutError(f"settlement reconciliation exceeded timeout={timeout}s")
    total = sum(entry["amount"] for entry in entries)
    return abs(total) < 1e-6
'''


def seed_0142(repo: Path) -> None:
    _write(repo / "ledger_core" / "settlement.py", SETTLEMENT_PY_0142)
    _git("add", "-A", cwd=repo)
    _git("commit", "-m", "settlement: add timeout guard for EOD reconciliation", cwd=repo)


PAYOUT_PY_0144 = '''"""Payout reconciliation for end-of-day ledger close."""

import os


def reconcile_payout(entries: list[dict], timeout: float = 0.5) -> bool:
    """True if the amounts net to zero (abs(sum) < 1e-6).

    Simulates load-dependent timeouts: about 30% of calls raise TimeoutError,
    standing in for real payout latency under load.
    """
    if os.urandom(1)[0] < 77:
        raise TimeoutError(f"payout reconciliation exceeded timeout={timeout}s")
    total = sum(entry["amount"] for entry in entries)
    return abs(total) < 1e-6
'''

TEST_PAYOUT_PY = '''from ledger_core.payout import reconcile_payout


def test_payout_reconciles_at_eod():
    entries = [{"amount": 42.0}, {"amount": -42.0}]
    assert reconcile_payout(entries) is True
'''


def seed_0144(repo: Path) -> None:
    _write(repo / "ledger_core" / "payout.py", PAYOUT_PY_0144)
    _write(repo / "tests" / "test_payout.py", TEST_PAYOUT_PY)
    _git("add", "-A", cwd=repo)
    _git("commit", "-m", "payout: add timeout guard for EOD reconciliation", cwd=repo)


VENDOR_HTTP_UTIL_0139 = '''"""Vendored stand-in for a third-party HTTP retry library (no network needed).

Simulated dependency bump: renamed Retry -> RetryPolicy.
"""


class RetryPolicy:
    def __init__(self, total: int = 3):
        self.total = total
'''


def seed_0139(repo: Path) -> None:
    # http_client.py is deliberately NOT updated: it still imports the old
    # `Retry` name, so collection fails with a real ImportError.
    _write(repo / "ledger_core" / "vendor" / "http_util.py", VENDOR_HTTP_UTIL_0139)
    _git("add", "-A", cwd=repo)
    _git("commit", "-m", "vendor/http_util: bump -- Retry renamed to RetryPolicy", cwd=repo)


ROLLUP_PY_0137 = '''"""Settlement window membership."""


def in_window(txn_date, start, end) -> bool:
    """True if txn_date falls within [start, end) -- end is exclusive."""
    return start <= txn_date <= end
'''


def seed_0137(repo: Path) -> None:
    # Only the operator changes; the docstring still says "end is exclusive"
    # on purpose -- real regressions rarely update the docs.
    _write(repo / "ledger_core" / "rollup.py", ROLLUP_PY_0137)
    _git("add", "-A", cwd=repo)
    _git("commit", "-m", "rollup: include boundary day in settlement window", cwd=repo)


ROUTES_PY_0131 = '''"""Ledger summary routes."""

from typing import Any
import os
import json


def get_ledger_summary(ledger_id: str) -> dict[str, Any]:
    return {
        "ledger_id": ledger_id,
        "status": "ok",
        "region": os.environ.get("LEDGER_REGION", "unset"),
    }
'''


def seed_0131(repo: Path) -> None:
    # Unused `json` import (F401) + unsorted import block (I001). Tests
    # still pass -- only ruff is red.
    _write(repo / "ledger_core" / "routes.py", ROUTES_PY_0131)
    _git("add", "-A", cwd=repo)
    _git("commit", "-m", "routes: add JSON helpers (WIP)", cwd=repo)


TEST_ENV_PY_0128 = '''import os


def test_region_config_present():
    assert os.environ["LEDGER_REGION"] in {"us-east", "us-west", "eu-west"}
'''


def seed_0128(repo: Path) -> None:
    _write(repo / "tests" / "test_env.py", TEST_ENV_PY_0128)
    _git("add", "-A", cwd=repo)
    _git("commit", "-m", "tests: assert deployment region is configured", cwd=repo)


CASE_SEEDERS: list[tuple[str, callable]] = [
    ("case/0142-flaky-settlement", seed_0142),
    ("case/0144-flaky-repeat", seed_0144),
    ("case/0139-dep-pin", seed_0139),
    ("case/0137-regression", seed_0137),
    ("case/0131-lint", seed_0131),
    ("case/0128-env-drift", seed_0128),
]


def already_seeded(repo: Path) -> bool:
    branches = _existing_branches(repo)
    return all(branch in branches for branch, _ in CASE_SEEDERS)


def build_repo(repo: Path) -> None:
    if repo.exists():
        shutil.rmtree(repo)
    repo.mkdir(parents=True)

    _git("init", "-b", "main", cwd=repo)
    # Force LF everywhere regardless of the outer repo's global autocrlf
    # setting, so files on disk always have \n endings (docs/06 requirement)
    # and `git archive` (the sandbox's checkout mechanism, §7) never rewrites them.
    _git("config", "core.autocrlf", "false", cwd=repo)
    _git("config", "core.eol", "lf", cwd=repo)

    write_main_branch(repo)
    _git("add", "-A", cwd=repo)
    _git("commit", "-m", "ledger-core: seed main (green)", cwd=repo)

    verify_main_green(repo)

    for branch, seeder in CASE_SEEDERS:
        _git("checkout", "-b", branch, "main", cwd=repo)
        seeder(repo)
        _git("checkout", "main", cwd=repo)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="rebuild from scratch")
    args = parser.parse_args()

    if not args.force and already_seeded(REPO_PATH):
        print(f"Already seeded: all six case branches exist in {REPO_PATH}")
        return

    print(f"Seeding {REPO_PATH} ...")
    build_repo(REPO_PATH)
    branch_list = ", ".join(branch for branch, _ in CASE_SEEDERS)
    print(f"Seeded. Branches: main, {branch_list}")


if __name__ == "__main__":
    main()
