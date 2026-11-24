from __future__ import annotations

from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from agent.nodes.ads import make_ads_node
from agent.nodes.compliance import make_compliance_node
from agent.nodes.executor import make_executor_node
from agent.nodes.insight import make_insight_node
from agent.nodes.listing import make_listing_node
from agent.nodes.supervisor import make_supervisor_node
from agent.services import Services
from agent.state import AgentState


def route_after_supervisor(state: AgentState) -> str:
    if state.get("errors"):
        return END
    return "ads" if state.get("mode") == "ads_only" else "insight"


def route_after_compliance(state: AgentState) -> str:
    return "ads" if state.get("mode") == "full_chain" else "executor"


def build_graph(
    services: Services,
    checkpointer: BaseCheckpointSaver | None = None,
):
    builder = StateGraph(AgentState)
    builder.add_node("supervisor", make_supervisor_node(services))
    builder.add_node("insight", make_insight_node(services))
    builder.add_node("listing", make_listing_node(services))
    builder.add_node("compliance", make_compliance_node(services))
    builder.add_node("ads", make_ads_node(services))
    builder.add_node("executor", make_executor_node(services))

    builder.add_edge(START, "supervisor")
    builder.add_conditional_edges(
        "supervisor",
        route_after_supervisor,
        {"insight": "insight", "ads": "ads", END: END},
    )
    builder.add_edge("insight", "listing")
    builder.add_edge("listing", "compliance")
    builder.add_conditional_edges(
        "compliance",
        route_after_compliance,
        {"ads": "ads", "executor": "executor"},
    )
    builder.add_edge("ads", "executor")
    builder.add_edge("executor", END)

    return builder.compile(
        checkpointer=checkpointer or MemorySaver(),
        interrupt_before=["executor"],
    )
