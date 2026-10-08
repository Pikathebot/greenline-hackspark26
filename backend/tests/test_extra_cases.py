"""B17: live-added cases (docs/plans/B17-live-case.md). No Docker or model needed."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from greenline.api.scoreboard import compute_scoreboard
from greenline.graph.cases import (
    BUILTIN_CASE_IDS,
    CASE_CONFIGS,
    FAILURE_CASES,
    all_case_ids,
    reload_extra_cases,
)

_spec = importlib.util.spec_from_file_location(
    "add_case", Path(__file__).resolve().parents[1] / "scripts" / "add_case.py"
)
add_case = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(add_case)


def _entry(case_id: str = "0151", **over) -> dict:
    return {
        "id": case_id,
        "branch": f"case/{case_id}-x",
        "title": "test_x",
        "cls": "regression",
        "failingTestNodeid": "tests/test_x.py::test_x",
        "patchTarget": "ledger_core/x.py",
        "fallbackCiLog": "FAILED tests/test_x.py::test_x",
        **over,
    }


@pytest.fixture(autouse=True)
def _restore_builtins():
    yield
    reload_extra_cases(Path("does-not-exist.json"))


def test_reload_adds_then_drops_extra_case(tmp_path):
    path = tmp_path / "extra_cases.json"
    path.write_text(json.dumps([_entry()]), encoding="utf-8")
    assert reload_extra_cases(path) == ["0151"]
    assert FAILURE_CASES["0151"].cls == "regression"
    assert CASE_CONFIGS["0151"].patch_target == "ledger_core/x.py"

    path.write_text("[]", encoding="utf-8")
    assert reload_extra_cases(path) == []
    assert "0151" not in FAILURE_CASES and "0151" not in CASE_CONFIGS


def test_builtins_are_never_replaced_or_dropped(tmp_path):
    path = tmp_path / "extra_cases.json"
    path.write_text(json.dumps([_entry("0142", cls="env"), _entry("abcd")]), encoding="utf-8")
    assert reload_extra_cases(path) == []
    assert FAILURE_CASES["0142"].cls == "flaky"
    assert tuple(FAILURE_CASES) == BUILTIN_CASE_IDS


def test_bad_class_and_corrupt_file_are_ignored(tmp_path):
    path = tmp_path / "extra_cases.json"
    path.write_text(json.dumps([_entry(cls="nonsense")]), encoding="utf-8")
    assert reload_extra_cases(path) == []
    path.write_text("{not json", encoding="utf-8")
    assert reload_extra_cases(path) == []


def test_all_case_ids_stays_builtin(tmp_path):
    path = tmp_path / "extra_cases.json"
    path.write_text(json.dumps([_entry()]), encoding="utf-8")
    reload_extra_cases(path)
    assert all_case_ids() == list(BUILTIN_CASE_IDS)


def test_scoreboard_ignores_extra_case_runs(db):
    db.insert_run("r-extra", "0151", "live", "normal", "2026-10-08T09:00:00Z")
    db.finish_run(
        "r-extra", status="complete", outcome="reported", ended_at="2026-10-08T09:01:00Z",
        model_calls=1, tool_calls=1, duration_ms=1000,
    )
    board = compute_scoreboard(db)
    assert board.sample_size == 0
    assert [p.case_id for p in board.per_case] == list(BUILTIN_CASE_IDS)


def test_parse_failing_nodeid():
    assert (
        add_case.parse_failing_nodeid("x\nFAILED tests/a.py::t - AssertionError: no\n")
        == "tests/a.py::t"
    )
    assert add_case.parse_failing_nodeid("ERROR tests/b.py - ImportError: nope") == "tests/b.py"
    ruff_only = "ledger_core/routes.py:1:1: F401 'json' imported but unused\n"
    assert add_case.parse_failing_nodeid(ruff_only) is None
