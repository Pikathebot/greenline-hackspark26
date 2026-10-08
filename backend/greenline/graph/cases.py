"""Static per-case config: the ONLY case-specific knowledge the graph gets
(docs/05-BACKEND-SPEC.md §9, docs/06-FIXTURE-REPO-SPEC.md § Case metadata).

Never put expected verdicts, outcomes or event sequences here. Ground-truth
`cls` is read only by the API/scoreboard, never by graph code (invariant 7).
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path

from greenline.events.models import FailureCase, FailureClass


@dataclass(frozen=True)
class CaseConfig:
    branch: str
    failing_test_nodeid: str | None  # None for lint (nothing to rerun)
    patch_target: str | None  # None when there's no safe automated fix (0128)
    fallback_ci_log: str  # used ONLY when the sandbox CI run fails for infra reasons


CASE_CONFIGS: dict[str, CaseConfig] = {
    "0142": CaseConfig(
        branch="case/0142-flaky-settlement",
        failing_test_nodeid="tests/test_settlement.py::test_settlement_reconciles_at_eod",
        patch_target="tests/test_settlement.py",
        fallback_ci_log=(
            "FAILED tests/test_settlement.py::test_settlement_reconciles_at_eod\n"
            "TimeoutError: settlement reconciliation exceeded timeout=0.5s"
        ),
    ),
    "0144": CaseConfig(
        branch="case/0144-flaky-repeat",
        failing_test_nodeid="tests/test_payout.py::test_payout_reconciles_at_eod",
        patch_target="tests/test_payout.py",
        fallback_ci_log=(
            "FAILED tests/test_payout.py::test_payout_reconciles_at_eod\n"
            "TimeoutError: payout reconciliation exceeded timeout=0.5s"
        ),
    ),
    "0139": CaseConfig(
        branch="case/0139-dep-pin",
        failing_test_nodeid="tests/test_http_client.py",
        patch_target="ledger_core/http_client.py",
        fallback_ci_log=(
            "ERROR tests/test_http_client.py - ImportError: cannot import name 'Retry' "
            "from 'ledger_core.vendor.http_util'"
        ),
    ),
    "0137": CaseConfig(
        branch="case/0137-regression",
        failing_test_nodeid="tests/test_rollup.py::test_reconcile_window_boundary",
        patch_target="ledger_core/rollup.py",
        fallback_ci_log=(
            "FAILED tests/test_rollup.py::test_reconcile_window_boundary\n"
            "AssertionError: assert in_window(date(2026, 9, 8), start, end) is False"
        ),
    ),
    "0131": CaseConfig(
        branch="case/0131-lint",
        failing_test_nodeid=None,
        patch_target="ledger_core/routes.py",
        fallback_ci_log=(
            "ledger_core/routes.py:1:1: F401 'json' imported but unused\n"
            "ledger_core/routes.py:1:1: I001 import block is un-sorted"
        ),
    ),
    "0128": CaseConfig(
        branch="case/0128-env-drift",
        failing_test_nodeid="tests/test_env.py::test_region_config_present",
        patch_target=None,
        fallback_ci_log=(
            "FAILED tests/test_env.py::test_region_config_present\n"
            "KeyError: 'LEDGER_REGION'"
        ),
    ),
}

# Cosmetic/display metadata for GET /api/cases. `cls` is ground truth: the
# scoreboard's only consumer of it. detectedAt timestamps are plausible event-day
# values; ciRunUrl is cosmetic.
FAILURE_CASES: dict[str, FailureCase] = {
    "0142": FailureCase(
        id="0142",
        title="test_settlement_reconciles_at_eod",
        repo="acme/ledger-core",
        branch=CASE_CONFIGS["0142"].branch,
        cls="flaky",
        detected_at="2026-10-08T10:42:00Z",
        ci_run_url="https://ci.example/acme/ledger-core/runs/142",
        beat="Restraint: proves the flake, refuses to edit the test",
    ),
    "0144": FailureCase(
        id="0144",
        title="test_payout_reconciles_at_eod",
        repo="acme/ledger-core",
        branch=CASE_CONFIGS["0144"].branch,
        cls="flaky",
        detected_at="2026-10-08T10:44:00Z",
        ci_run_url="https://ci.example/acme/ledger-core/runs/144",
        beat="Memory: recalls #0142, skips reproduction",
    ),
    "0139": FailureCase(
        id="0139",
        title="ImportError: cannot import name 'Retry'",
        repo="acme/ledger-core",
        branch=CASE_CONFIGS["0139"].branch,
        cls="dependency",
        detected_at="2026-10-08T10:39:00Z",
        ci_run_url="https://ci.example/acme/ledger-core/runs/139",
        beat="Happy path: one-line fix, draft PR",
    ),
    "0137": FailureCase(
        id="0137",
        title="test_reconcile_window_boundary",
        repo="acme/ledger-core",
        branch=CASE_CONFIGS["0137"].branch,
        cls="regression",
        detected_at="2026-10-08T10:37:00Z",
        ci_run_url="https://ci.example/acme/ledger-core/runs/137",
        beat="Patch to critique to re-patch",
    ),
    "0131": FailureCase(
        id="0131",
        title="ruff: F401 + I001 in routes.py",
        repo="acme/ledger-core",
        branch=CASE_CONFIGS["0131"].branch,
        cls="lint",
        detected_at="2026-10-08T10:31:00Z",
        ci_run_url="https://ci.example/acme/ledger-core/runs/131",
        beat="Cheapest run: tool fix, no model needed",
    ),
    "0128": FailureCase(
        id="0128",
        title="KeyError: 'LEDGER_REGION'",
        repo="acme/ledger-core",
        branch=CASE_CONFIGS["0128"].branch,
        cls="env",
        detected_at="2026-10-08T10:28:00Z",
        ci_run_url="https://ci.example/acme/ledger-core/runs/128",
        beat="Honest limits: no safe fix / budget exhausted",
    ),
}


# The six built-in cases. Anything else is a runtime "extra" case (B17): added by
# scripts/add_case.py, never counted by the scoreboard or `--cases all`.
BUILTIN_CASE_IDS: tuple[str, ...] = tuple(FAILURE_CASES)

_log = logging.getLogger(__name__)
_CASE_ID_RE = re.compile(r"^\d{4}$")
_CLASSES = ("flaky", "dependency", "regression", "lint", "env")


def load_extra_case_entries(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def save_extra_case_entries(path: Path, entries: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(entries, indent=2) + "\n", encoding="utf-8", newline="\n")


def reload_extra_cases(path: Path) -> list[str]:
    """Re-sync the extra (non-built-in) cases with `path`, mutating CASE_CONFIGS and
    FAILURE_CASES in place so every module that imported them sees the change.
    Cheap enough to call on every /api/cases request. Returns the loaded ids."""
    for case_id in [c for c in FAILURE_CASES if c not in BUILTIN_CASE_IDS]:
        del FAILURE_CASES[case_id]
        CASE_CONFIGS.pop(case_id, None)

    loaded: list[str] = []
    try:
        entries = load_extra_case_entries(path)
    except (OSError, ValueError) as exc:
        _log.warning("could not read %s: %s", path, exc)
        return loaded
    for entry in entries:
        case_id = str(entry.get("id", ""))
        if not _CASE_ID_RE.match(case_id) or case_id in BUILTIN_CASE_IDS or case_id in loaded:
            _log.warning("skipping extra case with bad or duplicate id %r", case_id)
            continue
        if entry.get("cls") not in _CLASSES:
            _log.warning("skipping extra case %s: bad cls %r", case_id, entry.get("cls"))
            continue
        CASE_CONFIGS[case_id] = CaseConfig(
            branch=entry["branch"],
            failing_test_nodeid=entry.get("failingTestNodeid"),
            patch_target=entry.get("patchTarget"),
            fallback_ci_log=entry.get("fallbackCiLog", ""),
        )
        FAILURE_CASES[case_id] = FailureCase(
            id=case_id,
            title=entry["title"],
            repo="acme/ledger-core",
            branch=entry["branch"],
            cls=entry["cls"],
            detected_at=entry.get("detectedAt", "2026-10-08T12:00:00Z"),
            ci_run_url=f"https://ci.example/acme/ledger-core/runs/{int(case_id)}",
            beat=entry.get("beat", "Added live"),
        )
        loaded.append(case_id)
    return loaded


def all_case_ids() -> list[str]:
    return list(BUILTIN_CASE_IDS)


def rerun_count_for(cls: FailureClass) -> int:
    """N by triage class (docs/05 §9 Reproducer): flaky 10, dependency/regression/env 3, lint 0."""
    if cls == "flaky":
        return 10
    if cls == "lint":
        return 0
    return 3
