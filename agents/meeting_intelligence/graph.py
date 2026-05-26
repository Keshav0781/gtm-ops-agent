"""
Meeting Intelligence Agent — Graph Definition

Connects all 4 nodes into complete workflow.

Flow:
START
  → extract_transcript
  → extract_action_items
  → generate_summary
  → prepare_notifications
END

Key difference from previous agents:
Nodes 1, 2, 3 are async — LLM calls
Node 4 is sync — pure formatting logic

No short-circuit routing needed here.
Every meeting regardless of type goes
through all 4 nodes.

"""

import logging
from langgraph.graph import StateGraph, START, END
from agents.meeting_intelligence.state import MeetingState
from agents.meeting_intelligence.nodes.extract_transcript import (
    extract_transcript
)
from agents.meeting_intelligence.nodes.extract_action_items import (
    extract_action_items
)
from agents.meeting_intelligence.nodes.generate_summary import (
    generate_summary
)
from agents.meeting_intelligence.nodes.prepare_notifications import (
    prepare_notifications
)

logger = logging.getLogger(__name__)


def should_continue(state: MeetingState) -> str:
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


def build_meeting_intelligence_graph() -> StateGraph:
    """
    Builds and compiles Meeting Intelligence Agent graph.
    """

    # ==========================================
    # Step 1 — Create graph with MeetingState
    # ==========================================
    graph = StateGraph(MeetingState)

    # ==========================================
    # Step 2 — Add all nodes
    # ==========================================
    graph.add_node("extract_transcript", extract_transcript)
    graph.add_node(
        "extract_action_items", extract_action_items
    )
    graph.add_node("generate_summary", generate_summary)
    graph.add_node(
        "prepare_notifications", prepare_notifications
    )

    # ==========================================
    # Step 3 — Entry point
    # ==========================================
    graph.add_edge(START, "extract_transcript")

    # ==========================================
    # Step 4 — Conditional edges after each node
    # ==========================================
    graph.add_conditional_edges(
        "extract_transcript",
        should_continue,
        {
            "continue": "extract_action_items",
            "stop": END
        }
    )

    graph.add_conditional_edges(
        "extract_action_items",
        should_continue,
        {
            "continue": "generate_summary",
            "stop": END
        }
    )

    graph.add_conditional_edges(
        "generate_summary",
        should_continue,
        {
            "continue": "prepare_notifications",
            "stop": END
        }
    )

    # ==========================================
    # Step 5 — Final node goes to END
    # ==========================================
    graph.add_edge("prepare_notifications", END)

    # ==========================================
    # Step 6 — Compile graph
    # ==========================================
    compiled_graph = graph.compile()

    logger.info(
        "Meeting Intelligence Graph compiled successfully"
    )

    return compiled_graph


# Create graph instance
meeting_intelligence_graph = build_meeting_intelligence_graph()