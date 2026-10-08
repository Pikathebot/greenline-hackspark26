"""B2: emitter invariants (docs/05-BACKEND-SPEC.md §3, docs/04-EVENT-CONTRACT.md).

- t = max(last_t, elapsed); out-of-order elapsed gets clamped, never decreases.
- seq is strictly increasing.
- a budget event follows every record_model_call()/record_tool_call().
"""

from __future__ import annotations

import json

from greenline.events.emitter import RunEmitter


def test_seq_strictly_increasing(db, bus):
    emitter = RunEmitter("run-1", db, bus)
    e0 = emitter.enter("watcher")
    e1 = emitter.narrate("watcher", "pulling the red build")
    e2 = emitter.exit("watcher", "ok")
    seqs = [row[0] for row in db.events_for("run-1")]
    assert seqs == [0, 1, 2]
    assert e0["type"] == "node.enter"
    assert e1["type"] == "log"
    assert e2["type"] == "node.exit"


def test_t_clamped_never_decreases(db, bus):
    # A fake clock that goes forward, then briefly backward.
    ticks = iter([0.0, 1.0, 2.0, 0.5, 3.0])
    emitter = RunEmitter("run-2", db, bus, clock=lambda: next(ticks))
    # clock() called once in __init__ (t=0.0 -> _start=0.0)
    first = emitter.emit("log", node="watcher", level="info", text="a")  # elapsed=(1.0-0.0)*1000=1000
    second = emitter.emit("log", node="watcher", level="info", text="b")  # elapsed=2000
    third = emitter.emit("log", node="watcher", level="info", text="c")  # elapsed=(0.5-0.0)*1000=500, clamped to 2000
    fourth = emitter.emit("log", node="watcher", level="info", text="d")  # elapsed=3000

    assert first["t"] == 1000
    assert second["t"] == 2000
    assert third["t"] == 2000  # clamped: never goes backward
    assert fourth["t"] == 3000

    ts = [row for row in db.events_for("run-2")]
    assert len(ts) == 4


def test_budget_follows_record_calls(db, bus):
    emitter = RunEmitter("run-3", db, bus)
    budget_event = emitter.record_model_call()
    assert budget_event["type"] == "budget"
    assert budget_event["modelCalls"] == 1
    assert budget_event["toolCalls"] == 0

    budget_event = emitter.record_tool_call()
    assert budget_event["type"] == "budget"
    assert budget_event["modelCalls"] == 1
    assert budget_event["toolCalls"] == 1

    # Every emitted event in the log is either the record's own trigger or a budget
    # event -- here, both calls are each exactly one budget event.
    types = [json.loads(row[1])["type"] for row in db.events_for("run-3")]
    assert types == ["budget", "budget"]


def test_node_exit_duration_from_enter(db, bus):
    # A settable clock avoids caring how many times _elapsed_ms() is called
    # per enter()/exit() (it calls clock() more than once internally).
    now = {"t": 0.0}
    emitter = RunEmitter("run-4", db, bus, clock=lambda: now["t"])
    now["t"] = 0.1
    emitter.enter("watcher")  # elapsed=100ms at enter
    now["t"] = 1.6
    exit_event = emitter.exit("watcher", "ok")  # elapsed=1600ms -> duration=1500ms
    assert exit_event["durationMs"] == 1500


def test_emit_publishes_to_bus(db, bus):
    emitter = RunEmitter("run-5", db, bus)
    queue = bus.subscribe("run-5")
    emitter.narrate("watcher", "hello")
    message = queue.get_nowait()
    assert message["seq"] == 0
    assert message["payload"]["type"] == "log"
