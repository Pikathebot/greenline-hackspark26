"""Graph assembly (docs/05-BACKEND-SPEC.md §9). No LangGraph checkpointer:
our persistence IS the event log.

B7 scope: watcher -> triage -> reproducer -> analyst -> reporter. Patcher
and Critic land at ticket B9. Until then, analyst's "not blocked" path
also routes to reporter (see graph/nodes/analyst.py's block_reason =
'no_patcher_yet') -- every conditional edge below checks budget_exhausted
first and short-circuits straight to reporter, per spec ("any budget
exhaustion goes straight to reporter").
"""

from __future__ import annotations

from langgraph.graph import END, StateGraph

from greenline.graph.nodes.analyst import analyst_node
from greenline.graph.nodes.reporter import reporter_node
from greenline.graph.nodes.reproducer import reproducer_node
from greenline.graph.nodes.triage import triage_node
from greenline.graph.nodes.watcher import watcher_node
from greenline.graph.state import GreenlineState


def _route_to(next_node: str):
    def _route(state: GreenlineState) -> str:
        if state.get("budget_exhausted"):
            return "reporter"
        return next_node

    return _route


def build_graph():
    graph = StateGraph(GreenlineState)
    graph.add_node("watcher", watcher_node)
    graph.add_node("triage", triage_node)
    graph.add_node("reproducer", reproducer_node)
    graph.add_node("analyst", analyst_node)
    graph.add_node("reporter", reporter_node)

    graph.set_entry_point("watcher")
    graph.add_conditional_edges(
        "watcher", _route_to("triage"), {"triage": "triage", "reporter": "reporter"}
    )
    graph.add_conditional_edges(
        "triage", _route_to("reproducer"), {"reproducer": "reproducer", "reporter": "reporter"}
    )
    graph.add_conditional_edges(
        "reproducer", _route_to("analyst"), {"analyst": "analyst", "reporter": "reporter"}
    )
    # analyst always decides blocked=True today (no Patcher/Critic until B9),
    # so this is effectively unconditional for now, but written as a real
    # conditional edge so B9 only needs to add a "patcher" branch here.
    graph.add_conditional_edges("analyst", _route_to("reporter"), {"reporter": "reporter"})
    graph.add_edge("reporter", END)

    return graph.compile()
