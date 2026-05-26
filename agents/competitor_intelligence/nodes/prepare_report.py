"""
Node 4 — Prepare Report

Final node in Competitor Intelligence Agent.
Formats all competitor analyses into a
clean weekly intelligence report for Slack.

No LLM needed — pure formatting logic.
Same reasoning as other final nodes.

Report sections:
1. Executive summary — what matters most
2. Per competitor breakdown
3. Recommended actions for sales team

"""

import logging
from agents.competitor_intelligence.state import (
    CompetitorState
)

logger = logging.getLogger(__name__)


def format_competitor_section(
    analysis: dict
) -> str:
    """
    Formats single competitor section for Slack.
    """
    name = analysis.get("name", "Unknown")
    url = analysis.get("url", "")
    changes_detected = analysis.get(
        "changes_detected", False
    )

    if analysis.get("error"):
        return (
            f"*{name}* ({url})\n"
            f"Status: Could not fetch — manual check needed\n"
        )

    if not changes_detected:
        return (
            f"*{name}* ({url})\n"
            f"No significant changes detected\n"
        )

    significant = analysis.get(
        "significant_changes", "None"
    )
    impact = analysis.get("business_impact", "None")
    action = analysis.get("recommended_action", "None")

    return (
        f"*{name}* ({url})\n"
        f"Changes: {significant}\n"
        f"Business Impact: {impact}\n"
        f"Recommended Action: {action}\n"
    )


def prepare_report(
    state: CompetitorState
) -> CompetitorState:
    """
    Node 4 — Prepare weekly competitive intelligence report.

    Not async — pure formatting logic.

    What it does:
    1. Checks if previous nodes failed
    2. Creates executive summary
    3. Formats per competitor sections
    4. Builds complete Slack report
    5. Marks agent as completed

    Input state fields used:
        competitor_analyses, total_changes_found,
        significant_changes, report_date,
        successful_scrapes, failed_scrapes

    Output state fields added:
        slack_report, report_summary,
        slack_channel, report_ready, completed
    """

    # ==========================================
    # Step 1 — Check if previous nodes failed
    # ==========================================
    if state.get("error"):
        logger.warning(
            f"[{state.get('request_id')}] "
            f"Node 4: Skipping — previous node failed"
        )
        return state

    analyses = state.get("competitor_analyses", [])
    total_changes = state.get("total_changes_found", 0)
    report_date = state.get("report_date", "This week")
    successful = state.get("successful_scrapes", 0)
    failed = state.get("failed_scrapes", 0)

    logger.info(
        f"[{state.get('request_id')}] "
        f"Node 4: Preparing competitive report"
    )

    # ==========================================
    # Step 2 — Build executive summary
    # ==========================================
    if total_changes == 0:
        exec_summary = (
            f"No significant competitor changes "
            f"detected this week. "
            f"Monitored {len(analyses)} competitors."
        )
    else:
        changed_names = [
            a["name"] for a in analyses
            if a.get("changes_detected")
        ]
        exec_summary = (
            f"{total_changes} competitor(s) with "
            f"significant changes this week: "
            f"{', '.join(changed_names)}. "
            f"Review details below."
        )

    # ==========================================
    # Step 3 — Format per competitor sections
    # ==========================================
    competitor_sections = []
    for analysis in analyses:
        section = format_competitor_section(analysis)
        competitor_sections.append(section)

    # ==========================================
    # Step 4 — Build complete Slack report
    # ==========================================
    report = (
        f"*Weekly Competitive Intelligence Report*\n"
        f"Week of {report_date} | "
        f"Monitored: {successful} sites | "
        f"Failed: {failed}\n\n"
        f"*Executive Summary:*\n"
        f"{exec_summary}\n\n"
        f"*Competitor Breakdown:*\n"
        f"{'=' * 40}\n"
    )

    for section in competitor_sections:
        report += f"\n{section}"
        report += f"{'—' * 30}\n"

    report += (
        f"\n_Report generated automatically. "
        f"Review and share with sales team._"
    )

    # ==========================================
    # Step 5 — Update state
    # ==========================================
    state["slack_report"] = report.strip()
    state["report_summary"] = exec_summary
    state["slack_channel"] = "#competitive-intelligence"
    state["report_ready"] = True
    state["completed"] = True

    logger.info(
        f"[{state.get('request_id')}] "
        f"Node 4: Report ready — "
        f"channel={state['slack_channel']}"
    )

    return state