"""Small helpers shared across nodes (and scripts/run_case.py)."""

from __future__ import annotations


def first_failing_line(output: str) -> str:
    """Best-effort extraction of the one line that explains why a CI run
    is red, for evidence/observation text and dev-script output."""
    for line in output.splitlines():
        stripped = line.strip()
        if stripped.startswith(("FAILED", "ERROR", "E   ")):
            return stripped
    for line in output.splitlines():
        stripped = line.strip()
        if any(marker in stripped for marker in ("F401", "I001", "Error", "Exception")):
            return stripped
    non_empty = [line for line in output.strip().splitlines() if line.strip()]
    return non_empty[-1] if non_empty else "(no output)"


def last_n_lines(text: str, n: int = 60) -> str:
    lines = text.splitlines()
    return "\n".join(lines[-n:])
