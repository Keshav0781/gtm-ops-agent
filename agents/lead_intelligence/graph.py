"""
Lead Intelligence Agent — Graph Definition

This file connects all 4 nodes into a 
complete agent workflow.

Flow:
START
  → parse_lead
  → research_company  
  → score_lead
  → draft_email
END

At each step — if error detected → go to END
immediately. No wasted LLM calls.
"""

import logging
from langgraph.graph import StateGraph, START, END
from agents.lead_intelligence.state import LeadState
from agents.lead_intelligence.nodes.parse_lead import (
    parse_lead
)
from agents.lead_intelligence.nodes.research_company import (
    research_company
)
from agents.lead_intelligence.nodes.score_lead import (
    score_lead
)
from agents.lead_intelligence.nodes.draft_email import (
    draft_email
)

logger = logging.getLogger(__name__)


def should_continue(state: LeadState) -> str:
    """
    Conditional edge function.
    Called after every node to check if
    we should continue or stop.

    Returns:
        "continue" — no errors, keep going
        "stop"     — error found, go to END

    """
    if state.get("error"):
        logger.warning(
            f"[{state.get('request_id')}] "
            f"Graph: Error detected — stopping. "
            f"Reason: {state.get('error')}"
        )
        return "stop"
    return "continue"


def build_lead_intelligence_graph() -> StateGraph:
    """
    Builds and compiles the Lead Intelligence Agent graph.

    Why we compile:
    LangGraph compiles the graph into an optimised
    runnable. Like compiling code — validates the
    graph structure and prepares it for execution.

    Returns compiled graph ready to run.
    """

    # ==========================================
    # Step 1 — Create graph with our state
    # ==========================================
    graph = StateGraph(LeadState)

    # ==========================================
    # Step 2 — Add all nodes to graph
    # ==========================================
    graph.add_node("parse_lead", parse_lead)
    graph.add_node("research_company", research_company)
    graph.add_node("score_lead", score_lead)
    graph.add_node("draft_email", draft_email)

    # ==========================================
    # Step 3 — Define entry point
    # Where does the graph start?
    # ==========================================
    graph.add_edge(START, "parse_lead")

    # ==========================================
    # Step 4 — Add conditional edges
    # After each node — check for errors
    # If error → stop
    # If no error → continue to next node
    # ==========================================
    graph.add_conditional_edges(
        "parse_lead",
        should_continue,
        {
            "continue": "research_company",
            "stop": END
        }
    )

    graph.add_conditional_edges(
        "research_company",
        should_continue,
        {
            "continue": "score_lead",
            "stop": END
        }
    )

    graph.add_conditional_edges(
        "score_lead",
        should_continue,
        {
            "continue": "draft_email",
            "stop": END
        }
    )

    # ==========================================
    # Step 5 — Final node goes to END
    # draft_email is last node — always end here
    # ==========================================
    graph.add_edge("draft_email", END)

    # ==========================================
    # Step 6 — Compile the graph
    # Validates structure and prepares for execution
    # ==========================================
    compiled_graph = graph.compile()

    logger.info("Lead Intelligence Graph compiled successfully")

    return compiled_graph


# Create graph instance
# This is imported by the FastAPI router
lead_intelligence_graph = build_lead_intelligence_graph()