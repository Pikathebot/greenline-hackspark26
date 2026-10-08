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
