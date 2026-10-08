"""B1: contract round-trip test (docs/04-EVENT-CONTRACT.md).

One valid instance of every GreenlineEvent variant, serialised and re-parsed.
Also exports frontend/src/state/__fixtures__/allVariants.json via
scripts/export_variants.py (run separately, not by pytest).
"""

from __future__ import annotations

from greenline.events.fixtures import ALL_VARIANTS
from greenline.events.models import (
    CaseSummary,
    ErrorEvent,
    FailureCase,
    NodeExitEvent,
    ReportEvent,
    RunSummary,
    dump_event,
    parse_event,
)


def test_all_variants_covered():
    from typing import get_args

    from greenline.events.models import GreenlineEvent

    union_type, _discriminator = get_args(GreenlineEvent)
    variant_count = len(get_args(union_type))
    assert len(ALL_VARIANTS) == variant_count


def test_round_trip():
    for name, event in ALL_VARIANTS.items():
        payload = dump_event(event)
        assert payload["type"] == name
        parsed = parse_event(payload)
        assert parsed == event


def test_camel_case_keys():
    event = ALL_VARIANTS["run.start"]
    payload = dump_event(event)
    assert "runId" in payload
    assert "run_id" not in payload
    assert "caseId" in payload
    assert "budgetPreset" in payload
    assert payload["caps"]["modelCalls"] == 16


def test_optional_fields_omitted_when_absent():
    event = NodeExitEvent(t=100, node="watcher", duration_ms=50, status="ok")
    payload = dump_event(event)
    assert "note" not in payload

    error = ErrorEvent(t=100, message="boom")
    payload = dump_event(error)
    assert "node" not in payload

    report = ReportEvent(t=100, kind="escalation", title="t", body="b")
    payload = dump_event(report)
    assert "prUrl" not in payload
    assert "dryRun" not in payload


def test_t_is_int_and_not_renamed():
    event = ALL_VARIANTS["node.enter"]
    payload = dump_event(event)
    assert payload["t"] == 120
    assert isinstance(payload["t"], int)


def test_failure_case_and_summaries_round_trip():
    case = FailureCase(
        id="0142",
        title="test_settlement_reconciles_at_eod",
        repo="acme/ledger-core",
        branch="case/0142-flaky-settlement",
        cls="flaky",
        detected_at="2026-10-08T11:00:00Z",
        ci_run_url="https://ci.example/runs/42",
        beat="A flaky test survives rerun pressure and reaches the right verdict.",
    )
    payload = case.model_dump(by_alias=True, exclude_none=True, mode="json")
    assert payload["detectedAt"] == "2026-10-08T11:00:00Z"
    assert payload["ciRunUrl"] == case.ci_run_url
    assert FailureCase.model_validate(payload) == case

    run_summary = RunSummary(
        run_id="run-1", outcome="reported", duration_ms=30_000, model_calls=7, tool_calls=5, mode="live"
    )
    summary = CaseSummary(**case.model_dump(), last_run=run_summary, has_demo_run=True)
    payload = summary.model_dump(by_alias=True, exclude_none=True, mode="json")
    assert payload["lastRun"]["runId"] == "run-1"
    assert payload["hasDemoRun"] is True
    assert CaseSummary.model_validate(payload) == summary

    # lastRun is a required-but-nullable field (TS: `RunSummary | null`), unlike the
    # event contract's omit-when-absent optionals, so the API must NOT exclude_none
    # here or the key would vanish instead of reading as explicitly null.
    cold = CaseSummary(**case.model_dump(), last_run=None, has_demo_run=False)
    payload = cold.model_dump(by_alias=True, mode="json")
    assert payload["lastRun"] is None
    assert CaseSummary.model_validate(payload) == cold
