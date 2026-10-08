"""Graph assembly (docs/05-BACKEND-SPEC.md §9). No LangGraph checkpointer:
our persistence IS the event log.

watcher -> triage -> reproducer -> analyst -> (reporter if blocked |
patcher) -> critic -> (patcher, max 2 attempts | reporter). Every
conditional edge checks budget_exhausted first and short-circuits
straight to reporter, per spec ("any budget exhaustion goes straight to
reporter") -- not just analyst's edge, so exhaustion mid-watcher or
mid-reproducer also routes correctly.
"""

from __future__ import annotations

from langgraph.graph import END, StateGraph

from greenline.graph.nodes.analyst import analyst_node
from greenline.graph.nodes.critic import critic_node
from greenline.graph.nodes.patcher import patcher_node
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


def _route_after_analyst(state: GreenlineState) -> str:
    if state.get("budget_exhausted"):
        return "reporter"
    if state.get("blocked"):
        return "reporter"
    return "patcher"


def _route_after_patcher(state: GreenlineState) -> str:
    if state.get("budget_exhausted"):
        return "reporter"
    attempts = state.get("patch_attempts") or []
    if not attempts or attempts[-1]["result"] == "vetoed":
        return "reporter"
    return "critic"


def _route_after_critic(state: GreenlineState) -> str:
    if state.get("budget_exhausted"):
        return "reporter"
    if state.get("critic_approved"):
        return "reporter"
    if len(state.get("patch_attempts") or []) < 2:
        return "patcher"
    return "reporter"


def build_graph():
    graph = StateGraph(GreenlineState)
    graph.add_node("watcher", watcher_node)
    graph.add_node("triage", triage_node)
    graph.add_node("reproducer", reproducer_node)
    graph.add_node("analyst", analyst_node)
    graph.add_node("patcher", patcher_node)
    graph.add_node("critic", critic_node)
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
    graph.add_conditional_edges(
        "analyst", _route_after_analyst, {"patcher": "patcher", "reporter": "reporter"}
    )
    graph.add_conditional_edges(
        "patcher", _route_after_patcher, {"critic": "critic", "reporter": "reporter"}
    )
    graph.add_conditional_edges(
        "critic", _route_after_critic, {"patcher": "patcher", "reporter": "reporter"}
    )
    graph.add_edge("reporter", END)

    return graph.compile()
