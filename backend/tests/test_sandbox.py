"""B5 acceptance (docs/05-BACKEND-SPEC.md §7, §12.7, docs/06's table).

Real Docker, real fixture repo -- excluded from the default `pytest` run
(see pyproject.toml's addopts). Run explicitly with:
    .venv\\Scripts\\python.exe -m pytest -m slow tests\\test_sandbox.py -v
"""

from __future__ import annotations

import subprocess

import docker
import pytest

from greenline.config import get_settings
from greenline.graph.cases import CASE_CONFIGS
from greenline.sandbox.runner import SandboxRunner

pytestmark = pytest.mark.slow


@pytest.fixture(scope="module")
def runner() -> SandboxRunner:
    settings = get_settings()
    return SandboxRunner(settings.fixture_repo_path(), settings.sandbox_image)


def test_main_is_green(runner: SandboxRunner):
    result = runner.run_ci("main")
    assert result.passed, result.stdout + result.stderr


@pytest.mark.parametrize(
    "case_id,needle",
    [
        ("0139", "cannot import name 'Retry'"),
        ("0137", "test_reconcile_window_boundary"),
        ("0128", "LEDGER_REGION"),
    ],
)
def test_run_ci_fails_for_the_right_reason(runner: SandboxRunner, case_id, needle):
    branch = CASE_CONFIGS[case_id].branch
    result = runner.run_ci(branch)
    assert not result.passed
    assert needle in result.stdout + result.stderr


def test_lint_case_tests_pass_but_ruff_fails(runner: SandboxRunner):
    branch = CASE_CONFIGS["0131"].branch
    result = runner.run_ci(branch)
    assert not result.passed  # run_ci's combined exit is "first non-zero"; here ruff's
    assert "F401" in result.stdout or "I001" in result.stdout


def test_ruff_fix_resolves_the_lint_case(runner: SandboxRunner):
    config = CASE_CONFIGS["0131"]
    fixed = runner.ruff_fix(config.branch, config.patch_target)
    assert "import json" not in fixed.stdout
    # feed the fixed content back through run_patched to confirm it's fully green
    verified = runner.run_patched(config.branch, config.patch_target, fixed.stdout)
    assert verified["tests_passed"]
    assert verified["lint_passed"]


def test_run_patched_distinguishes_green_from_red(runner: SandboxRunner):
    branch = CASE_CONFIGS["0139"].branch
    target = CASE_CONFIGS["0139"].patch_target

    good_fix = (
        '"""Thin wrapper around the vendored retry policy."""\n\n'
        "from ledger_core.vendor.http_util import RetryPolicy\n\n\n"
        "def make_retry_policy() -> RetryPolicy:\n"
        "    return RetryPolicy(total=3)\n"
    )
    good = runner.run_patched(branch, target, good_fix)
    assert good["tests_passed"] is True
    assert good["lint_passed"] is True

    bad_fix = (
        '"""broken."""\n\n'
        "from ledger_core.vendor.http_util import Retry\n\n\n"
        "def make_retry_policy():\n"
        "    return Retry(total=3)\n"
    )
    bad = runner.run_patched(branch, target, bad_fix)
    assert bad["tests_passed"] is False


def test_read_file_and_breaking_diff(runner: SandboxRunner):
    branch = CASE_CONFIGS["0137"].branch
    content = runner.read_file(branch, "ledger_core/rollup.py")
    assert "end is exclusive" in content
    assert "txn_date <= end" in content  # the regression itself

    diff = runner.breaking_diff(branch)
    assert "-    return start <= txn_date < end" in diff
    assert "+    return start <= txn_date <= end" in diff


def test_flaky_rerun_shows_a_genuinely_mixed_distribution(runner: SandboxRunner):
    config = CASE_CONFIGS["0142"]
    outcomes = {runner.run_test(config.branch, config.failing_test_nodeid).passed for _ in range(10)}
    # ~30% per-run failure rate; P(10/10 identical) ~= 0.7^10 + 0.3^10 ~= 2.9%.
    # Flaky by design -- if this ever flakes, it's telling you the truth.
    assert outcomes == {True, False}


def test_no_leftover_containers(runner: SandboxRunner):
    client = docker.from_env()
    before = {c.id for c in client.containers.list(all=True)}
    runner.run_ci("main")
    after = {c.id for c in client.containers.list(all=True)}
    assert after == before


def test_fresh_container_per_call_no_state_leaks(runner: SandboxRunner):
    # If a container were reused, a file written in one call could bleed
    # into the next. Confirm two run_ci calls are fully independent.
    first = runner.run_ci("main")
    second = runner.run_ci("main")
    assert first.passed and second.passed
    assert first.command == second.command
