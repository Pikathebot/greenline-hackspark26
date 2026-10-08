"""Small helpers shared across nodes (and scripts/run_case.py)."""

from __future__ import annotations

import re


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


def test_name_for(config) -> str:
    """Short test identifier for the memory embedding query text
    (docs/05 §9: embed "{test name}: {rationale}"). Using just the test's
    own name (not its file path) lets #0142 and #0144's differently-named
    files still match on the shared "reconciles_at_eod" shape."""
    nodeid = getattr(config, "failing_test_nodeid", None)
    if nodeid:
        return nodeid.split("::")[-1]
    return getattr(config, "patch_target", None) or "unknown"


def parse_failing_nodeid(output: str) -> str | None:
    """First `FAILED <nodeid>` / `ERROR <nodeid>` line of pytest output, minus any ` - msg`."""
    for line in output.splitlines():
        m = re.match(r"^(?:FAILED|ERROR)\s+(\S+)", line.strip())
        if m:
            return m.group(1)
    return None


def failing_lines(output: str, limit: int = 2) -> str:
    """The few lines that best explain a red CI run, for a case's fallback log."""
    stripped = [ln.strip() for ln in output.splitlines()]
    summary = [ln for ln in stripped if ln.startswith(("FAILED", "ERROR"))]
    detail = [ln for ln in stripped if ln.startswith("E   ") or re.search(r"\b[A-Z]\d{3}\b", ln)]
    # pytest's short-summary lines read best; fall back to assertion detail / ruff findings.
    return "\n".join((summary or detail)[:limit]) or first_failing_line(output)
