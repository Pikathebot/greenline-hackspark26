"""B4 acceptance: seed_repo.py builds a real, green main and six case
branches, each failing for the right reason (docs/06-FIXTURE-REPO-SPEC.md).

Runs against a tmp_path copy, never the real backend/fixtures/ledger-core.
"""

from __future__ import annotations

import subprocess
import sys

import pytest

from scripts.seed_repo import CASE_SEEDERS, already_seeded, build_repo


@pytest.fixture(scope="module")
def seeded_repo(tmp_path_factory):
    repo = tmp_path_factory.mktemp("ledger-core-seed-test") / "ledger-core"
    build_repo(repo)  # raises if main isn't green -- the real B4 acceptance check
    return repo


def _checkout(repo, branch):
    subprocess.run(["git", "checkout", "-q", branch], cwd=repo, check=True)


def _pytest_ok(repo) -> tuple[bool, str]:
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"], cwd=repo, capture_output=True, text=True
    )
    return result.returncode == 0, result.stdout + result.stderr


def _ruff_ok(repo) -> tuple[bool, str]:
    result = subprocess.run(
        [sys.executable, "-m", "ruff", "check", "."], cwd=repo, capture_output=True, text=True
    )
    return result.returncode == 0, result.stdout + result.stderr


def test_all_six_case_branches_exist(seeded_repo):
    assert already_seeded(seeded_repo)
    assert len(CASE_SEEDERS) == 6


def test_main_is_green(seeded_repo):
    _checkout(seeded_repo, "main")
    ok, out = _pytest_ok(seeded_repo)
    assert ok, out
    ok, out = _ruff_ok(seeded_repo)
    assert ok, out


@pytest.mark.parametrize(
    "branch,pytest_should_pass,ruff_should_pass,needle",
    [
        ("case/0139-dep-pin", False, True, "cannot import name 'Retry'"),
        ("case/0137-regression", False, True, "test_reconcile_window_boundary"),
        ("case/0131-lint", True, False, "F401"),
        ("case/0128-env-drift", False, True, "LEDGER_REGION"),
    ],
)
def test_deterministic_branch_fails_for_the_right_reason(
    seeded_repo, branch, pytest_should_pass, ruff_should_pass, needle
):
    _checkout(seeded_repo, branch)
    pytest_passed, pytest_out = _pytest_ok(seeded_repo)
    ruff_passed, ruff_out = _ruff_ok(seeded_repo)
    assert pytest_passed is pytest_should_pass, pytest_out
    assert ruff_passed is ruff_should_pass, ruff_out
    combined = pytest_out + ruff_out
    assert needle in combined, combined


def test_lint_branch_is_safely_autofixable(seeded_repo, tmp_path):
    # ruff --fix must resolve BOTH F401 and I001 without --unsafe-fixes
    # (docs/06 acceptance for B3/seed time), or the Patcher's tool-first
    # path (ticket B9) has nothing reliable to call.
    _checkout(seeded_repo, "case/0131-lint")
    target = seeded_repo / "ledger_core" / "routes.py"
    fix_result = subprocess.run(
        [sys.executable, "-m", "ruff", "check", "--fix", str(target)],
        cwd=seeded_repo,
        capture_output=True,
        text=True,
    )
    assert fix_result.returncode == 0, fix_result.stdout + fix_result.stderr
    ok, out = _ruff_ok(seeded_repo)
    assert ok, out
    ok, out = _pytest_ok(seeded_repo)
    assert ok, out
    # restore the branch to its committed (lint-dirty) state for the next test
    subprocess.run(["git", "checkout", "-q", "--", "."], cwd=seeded_repo, check=True)


def test_flaky_branches_use_os_urandom_not_a_fixed_outcome(seeded_repo):
    # Fresh interpreter per rerun (as the real sandbox does, one container
    # each), enough samples to make an always-pass/always-fail bug visible.
    for branch in ("case/0142-flaky-settlement", "case/0144-flaky-repeat"):
        _checkout(seeded_repo, branch)
        outcomes = set()
        for _ in range(12):
            ok, _ = _pytest_ok(seeded_repo)
            outcomes.add(ok)
            if len(outcomes) == 2:
                break
        assert outcomes == {True, False}, f"{branch}: no variance across 12 fresh runs"


def test_files_on_disk_use_lf_only(seeded_repo):
    _checkout(seeded_repo, "main")
    for relative in ("ledger_core/settlement.py", "pyproject.toml", "tests/test_rollup.py"):
        raw = (seeded_repo / relative).read_bytes()
        assert b"\r\n" not in raw, relative
