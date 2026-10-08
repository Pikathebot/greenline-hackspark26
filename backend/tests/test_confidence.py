"""docs/05-BACKEND-SPEC.md §8/§12.4: one assertion per confidence table row."""

from __future__ import annotations

from greenline.graph.confidence import confidence
from greenline.sandbox.runner import TestResult


def _results(*outcomes: bool) -> list[TestResult]:
    return [
        TestResult(passed=p, exit_code=0 if p else 1, stdout="", stderr="", duration_ms=100, command="x")
        for p in outcomes
    ]


def test_flaky_mixed_reruns():
    reruns = _results(True, True, True, False, True, True, True, False, True, True)  # 8/10, 2 fail
    assert confidence("flaky", reruns, None) == 0.80 + 0.15 * min(1, 10 / 10)


def test_flaky_memory_hit():
    assert confidence("flaky", [], {"similarity": 0.88}) == 0.88
    assert confidence("flaky", [], {"similarity": 0.99}) == 0.95  # capped


def test_flaky_all_pass():
    assert confidence("flaky", _results(True, True, True), None) == 0.50


def test_flaky_all_fail():
    assert confidence("flaky", _results(False, False, False), None) == 0.30


def test_dependency_all_fail_same_type():
    assert confidence("dependency", _results(False, False, False), None) == 0.92


def test_regression_all_fail_same_type():
    assert confidence("regression", _results(False, False, False), None) == 0.92


def test_dependency_mixed():
    assert confidence("dependency", _results(True, False, False), None) == 0.50


def test_env_all_fail_missing_config():
    assert confidence("env", _results(False, False, False), None) == 0.90


def test_env_mixed_falls_through_to_default():
    assert confidence("env", _results(True, False, False), None) == 0.60


def test_lint_ruff_fails_tests_pass():
    assert confidence("lint", [], None) == 0.97


def test_anything_else_defaults_to_0_60():
    assert confidence("flaky", [], None) == 0.60
    assert confidence("dependency", [], None) == 0.60
    assert confidence("env", [], None) == 0.60
