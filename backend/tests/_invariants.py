"""Shared contract invariant checks (docs/04-EVENT-CONTRACT.md § Invariants
1-6), reused by tests/test_graph.py (real stack) and tests/test_termination.py
(fake LLM + fake sandbox). Invariant 7 (ground-truth cls never read by graph
code) is a structural property, checked separately in test_termination.py.
"""

from __future__ import annotations


def assert_contract_invariants(events: list[dict]) -> None:
    assert events, "no events at all"

    # 1. First event is run.start with t=0. Last is done. Exactly one done.
    assert events[0]["type"] == "run.start"
    assert events[0]["t"] == 0
    assert events[-1]["type"] == "done"
    done_events = [e for e in events if e["type"] == "done"]
    assert len(done_events) == 1, f"expected exactly one done, got {len(done_events)}"

    # 2. t is monotonic non-decreasing.
    ts = [e["t"] for e in events]
    assert ts == sorted(ts), "t is not monotonic non-decreasing"

    # 3. Every node.enter has a matching node.exit before the next node.enter.
    active_node = None
    for event in events:
        if event["type"] == "node.enter":
            assert active_node is None, f"two nodes active at once: {active_node} and {event['node']}"
            active_node = event["node"]
        elif event["type"] == "node.exit":
            assert active_node == event["node"], (
                f"exit for {event['node']!r} but {active_node!r} was the active node"
            )
            active_node = None
    assert active_node is None, f"{active_node!r} entered but never exited"

    # 4. At most one verdict.
    verdicts = [e for e in events if e["type"] == "verdict"]
    assert len(verdicts) <= 1, f"expected at most one verdict, got {len(verdicts)}"

    # 5. rerun.tick.n counts 1..total in order.
    rerun_ticks = [e for e in events if e["type"] == "rerun.tick"]
    if rerun_ticks:
        total = rerun_ticks[0]["total"]
        assert [t["n"] for t in rerun_ticks] == list(range(1, len(rerun_ticks) + 1))
        assert all(t["total"] == total for t in rerun_ticks)

    # 6. report is emitted before done for reported/escalated/budget_exhausted.
    # Optional for error.
    outcome = done_events[0]["outcome"]
    if outcome in ("reported", "escalated", "budget_exhausted"):
        reports = [e for e in events if e["type"] == "report"]
        assert reports, f"outcome {outcome!r} requires a report before done"
        report_index = events.index(reports[0])
        done_index = events.index(done_events[0])
        assert report_index < done_index, "report must come before done"
