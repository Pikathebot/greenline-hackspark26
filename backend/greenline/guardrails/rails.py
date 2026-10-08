"""Guardrails (docs/02-DECISIONS.md D16, docs/05-BACKEND-SPEC.md §9).

Principle: Greenline never edits tests to make them pass. This is why
#0142 and #0144 escalate, and it's the restraint thesis of the demo.
"""

from __future__ import annotations

import fnmatch

PROTECTED_GLOBS = [
    "tests/**",
    "**/migrations/**",
    "**/*secret*",
    ".github/workflows/**",
]


MAX_DIFF_LINES = 80


def diff_within_cap(diff: str, max_lines: int = MAX_DIFF_LINES) -> bool:
    """True if the number of changed (+/-) lines is within the cap.
    Excludes the unified diff's own ---/+++ file headers."""
    changed = 0
    for line in diff.splitlines():
        if line.startswith(("+++", "---")):
            continue
        if line.startswith(("+", "-")):
            changed += 1
    return changed <= max_lines


def is_main_or_master(branch: str) -> bool:
    """no_main_write: the Patcher's target branch must never be main/master.
    We always construct fix/<caseId> ourselves, so this is "checked, clear"
    by construction -- the same spirit as no_creds/egress_off."""
    return branch in ("main", "master")


def protected_file(paths: list[str]) -> bool:
    """True if ANY of `paths` matches a protected glob.

    fnmatch's `*` already matches across `/` (unlike shell globbing), which
    makes plain fnmatch handle most of these globs correctly on its own.
    The one gap: a `**/x/**`-style pattern requires a literal `/` before
    `x`, so it misses a path with no leading directory at all (bare
    `migrations/foo.py`). The stripped-prefix fallback below covers that.
    """
    for path in paths:
        normalized = path.replace("\\", "/").lstrip("/")
        for pattern in PROTECTED_GLOBS:
            if fnmatch.fnmatch(normalized, pattern):
                return True
            if pattern.startswith("**/") and fnmatch.fnmatch(normalized, pattern[3:]):
                return True
    return False
