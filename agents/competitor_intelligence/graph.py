"""
Competitor Intelligence Agent — Graph Definition

Connects all 4 nodes into complete workflow.

Flow:
START
  → define_competitors
  → scrape_competitors
  → analyze_changes
  → prepare_report
END

Note on execution time:
This agent is slower than others because:
- scrape_competitors makes real HTTP requests
- 3 second delay between each page fetch
- 2 competitors × 4 pages × 3 seconds = ~24 seconds

This is intentional — respectful scraping.
"""

import logging
from langgraph.graph import StateGraph, START, END
from agents.competitor_intelligence.state import (
    CompetitorState
)
from agents.competitor_intelligence.nodes.define_competitors import (
    define_competitors
)
from agents.competitor_intelligence.nodes.scrape_competitors import (
    scrape_competitors
)
from agents.competitor_intelligence.nodes.analyze_changes import (
    analyze_changes
)
from agents.competitor_intelligence.nodes.prepare_report import (
    prepare_report
)

logger = logging.getLogger(__name__)


def should_continue(state: CompetitorState) -> str:
    """
    Conditional edge — same pattern across all agents.
    """
    if state.get("error"):
        logger.warning(
            f"[{state.get('request_id')}] "
            f"Graph: Error detected — stopping. "
            f"Reason: {state.get('error')}"
        )
        return "stop"
    return "continue"


def build_competitor_intelligence_graph() -> StateGraph:
    """
    Builds and compiles Competitor Intelligence graph.
    """

    graph = StateGraph(CompetitorState)

    graph.add_node("define_competitors", define_competitors)
    graph.add_node("scrape_competitors", scrape_competitors)
    graph.add_node("analyze_changes", analyze_changes)
    graph.add_node("prepare_report", prepare_report)

    graph.add_edge(START, "define_competitors")

    graph.add_conditional_edges(
        "define_competitors",
        should_continue,
        {
            "continue": "scrape_competitors",
            "stop": END
        }
    )

    graph.add_conditional_edges(
        "scrape_competitors",
        should_continue,
        {
            "continue": "analyze_changes",
            "stop": END
        }
    )

    graph.add_conditional_edges(
        "analyze_changes",
        should_continue,
        {
            "continue": "prepare_report",
            "stop": END
        }
    )

    graph.add_edge("prepare_report", END)

    compiled_graph = graph.compile()

    logger.info(
        "Competitor Intelligence Graph "
        "compiled successfully"
    )

    return compiled_graph


competitor_intelligence_graph = (
    build_competitor_intelligence_graph()
)