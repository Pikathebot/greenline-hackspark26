"""Evidence-derived confidence (docs/05-BACKEND-SPEC.md §8). NOT the
model's own self-reported number: in the prototype it answered 0.95 on
every run, so it's never trusted (docs/02-DECISIONS.md § lessons)."""

from __future__ import annotations

from greenline.events.models import FailureClass
from greenline.sandbox.runner import TestResult


def confidence(
    cls: FailureClass,
    reruns: list[TestResult],
    memory_hit: dict | None,
) -> float:
    if cls == "lint":
        # Reproducer skips lint entirely (N=0); by definition Triage only
        # reaches `lint` when the Watcher's CI run already showed ruff
        # failing with tests passing.
        return 0.97

    fails = sum(1 for r in reruns if not r.passed)
    n = len(reruns)

    if cls == "flaky":
        if memory_hit is not None:
            return min(0.95, memory_hit["similarity"])
        if n == 0:
            return 0.60
        if fails == 0:
            return 0.50  # flake not observed
        if fails == n:
            return 0.30  # contradicts flaky
        return 0.80 + 0.15 * min(1, n / 10)  # genuinely mixed

    if cls in ("dependency", "regression"):
        if n == 0:
            return 0.60
        if fails == n:
            return 0.92  # all N reruns fail with the same error type
        return 0.50  # mixed

    if cls == "env":
        if n == 0:
            return 0.60
        if fails == n:
            return 0.90  # all reruns fail with the missing-config signature
        return 0.60

    return 0.60
