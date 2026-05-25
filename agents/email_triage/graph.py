"""
Email Triage Agent — Graph Definition

Connects all 4 nodes into complete workflow.

Flow:
START
  → classify_email
  → extract_context
  → draft_reply
  → route_email
END

Key difference from Lead Intelligence graph:
route_email node is NOT async — rule based.
LangGraph handles both async and sync nodes
seamlessly in same graph.
"""

import logging
from langgraph.graph import StateGraph, START, END
from agents.email_triage.state import EmailState
from agents.email_triage.nodes.classify_email import (
    classify_email
)
from agents.email_triage.nodes.extract_context import (
    extract_context
)
from agents.email_triage.nodes.draft_reply import (
    draft_reply
)
from agents.email_triage.nodes.route_email import (
    route_email
)

logger = logging.getLogger(__name__)


def should_continue(state: EmailState) -> str:
    """
    Conditional edge — same pattern as Lead Intelligence.
    Checks for errors after every node.
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


def should_skip_for_spam(state: EmailState) -> str:
    """
    Additional conditional edge after classify_email.
    If email is SPAM — skip to route_email directly.
    No context extraction or reply drafting needed.
    Saves two unnecessary LLM calls for spam.

    This is called short-circuit routing —
    skipping unnecessary steps when outcome
    is already clear.

    """
    if state.get("error"):
        return "stop"
    if state.get("classification") == "SPAM":
        logger.info(
            f"[{state.get('request_id')}] "
            f"Graph: SPAM detected — "
            f"short-circuiting to route"
        )
        return "spam"
    return "continue"


def build_email_triage_graph() -> StateGraph:
    """
    Builds and compiles Email Triage Agent graph.
    """

    # ==========================================
    # Step 1 — Create graph with EmailState
    # ==========================================
    graph = StateGraph(EmailState)

    # ==========================================
    # Step 2 — Add all nodes
    # ==========================================
    graph.add_node("classify_email", classify_email)
    graph.add_node("extract_context", extract_context)
    graph.add_node("draft_reply", draft_reply)
    graph.add_node("route_email", route_email)

    # ==========================================
    # Step 3 — Entry point
    # ==========================================
    graph.add_edge(START, "classify_email")

    # ==========================================
    # Step 4 — After classify_email
    # Three possible paths:
    # 1. Error → END
    # 2. SPAM → skip to route_email
    # 3. Normal → extract_context
    # ==========================================
    graph.add_conditional_edges(
        "classify_email",
        should_skip_for_spam,
        {
            "continue": "extract_context",
            "spam": "route_email",
            "stop": END
        }
    )

    # ==========================================
    # Step 5 — After extract_context
    # ==========================================
    graph.add_conditional_edges(
        "extract_context",
        should_continue,
        {
            "continue": "draft_reply",
            "stop": END
        }
    )

    # ==========================================
    # Step 6 — After draft_reply
    # ==========================================
    graph.add_conditional_edges(
        "draft_reply",
        should_continue,
        {
            "continue": "route_email",
            "stop": END
        }
    )

    # ==========================================
    # Step 7 — Final node goes to END
    # ==========================================
    graph.add_edge("route_email", END)

    # ==========================================
    # Step 8 — Compile graph
    # ==========================================
    compiled_graph = graph.compile()

    logger.info(
        "Email Triage Graph compiled successfully"
    )

    return compiled_graph


# Create graph instance
email_triage_graph = build_email_triage_graph()