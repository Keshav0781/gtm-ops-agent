"""
CRM Hygiene Agent — Graph Definition

Connects all 4 nodes into complete workflow.

Flow:
START
  → fetch_deals
  → analyze_deals
  → prioritize_alerts
  → prepare_alerts
END

Key difference from other agents:
ALL nodes are synchronous — no LLM calls
except optional follow-up email drafting
added in Phase 12 feedback loop.

Pure Python logic throughout.
Fastest agent in our system.
Typical execution: under 500ms
regardless of deal count.

"""

import logging
from langgraph.graph import StateGraph, START, END
from agents.crm_hygiene.state import CRMState
from agents.crm_hygiene.nodes.fetch_deals import (
    fetch_deals
)
from agents.crm_hygiene.nodes.analyze_deals import (
    analyze_deals
)
from agents.crm_hygiene.nodes.prioritize_alerts import (
    prioritize_alerts
)
from agents.crm_hygiene.nodes.prepare_alerts import (
    prepare_alerts
)

logger = logging.getLogger(__name__)


def should_continue(state: CRMState) -> str:
    """
    Conditional edge — same pattern across all agents.
    Stops immediately if error detected.
    """
    if state.get("error"):
        logger.warning(
            f"[{state.get('request_id')}] "
            f"Graph: Error detected — stopping. "
            f"Reason: {state.get('error')}"
        )
        return "stop"
    return "continue"


def build_crm_hygiene_graph() -> StateGraph:
    """
    Builds and compiles CRM Hygiene Agent graph.
    """

    graph = StateGraph(CRMState)

    graph.add_node("fetch_deals", fetch_deals)
    graph.add_node("analyze_deals", analyze_deals)
    graph.add_node("prioritize_alerts", prioritize_alerts)
    graph.add_node("prepare_alerts", prepare_alerts)

    graph.add_edge(START, "fetch_deals")

    graph.add_conditional_edges(
        "fetch_deals",
        should_continue,
        {
            "continue": "analyze_deals",
            "stop": END
        }
    )

    graph.add_conditional_edges(
        "analyze_deals",
        should_continue,
        {
            "continue": "prioritize_alerts",
            "stop": END
        }
    )

    graph.add_conditional_edges(
        "prioritize_alerts",
        should_continue,
        {
            "continue": "prepare_alerts",
            "stop": END
        }
    )

    graph.add_edge("prepare_alerts", END)

    compiled_graph = graph.compile()

    logger.info("CRM Hygiene Graph compiled successfully")

    return compiled_graph


crm_hygiene_graph = build_crm_hygiene_graph()