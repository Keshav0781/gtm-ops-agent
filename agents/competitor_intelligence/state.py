"""
Competitor Intelligence Agent — State Definition

Shared notebook flowing through all 4 nodes.

Flow:
define_competitors → scrape_competitors →
analyze_changes → prepare_report

This agent fetches its own data from web.
No user provides competitor content.
Agent visits public websites automatically.

Legal note:
Only visits publicly accessible pages.
Respects robots.txt.
Rate limited — 3 second delay between requests.
No login required pages accessed.
Same approach used by Crayon, Klue, Kompyte
— all legitimate competitor intelligence tools.


Business value:
Sales team starts Monday knowing exactly
what competitors changed last week.
No manual monitoring needed.
Never miss a competitor pricing change again.
"""

from typing import Optional, List
from typing_extensions import TypedDict


class CompetitorData(TypedDict):
    """
    Data for one competitor website.
    Stores both current and previous content
    for comparison.
    """
    name: str
    url: str
    pages_to_check: List[str]    # homepage, pricing,
                                  # blog, careers
    current_content: Optional[dict]
    previous_content: Optional[dict]
    changes_detected: Optional[bool]
    changes_summary: Optional[str]
    fetch_error: Optional[str]


class CompetitorState(TypedDict):
    """
    Complete state for Competitor Intelligence Agent.
    """

    # ==========================================
    # INPUT — competitor list
    # Provided in request body
    # In Phase 8 stored in database and
    # fetched automatically by n8n scheduler
    # ==========================================
    competitors: Optional[List[dict]]
    report_date: Optional[str]

    # ==========================================
    # SCRAPED DATA — from scrape_competitors
    # Raw content fetched from each competitor
    # ==========================================
    scraped_data: Optional[List[CompetitorData]]
    successful_scrapes: Optional[int]
    failed_scrapes: Optional[int]

    # ==========================================
    # ANALYSIS — from analyze_changes
    # LLM analysis of what changed
    # ==========================================
    competitor_analyses: Optional[List[dict]]
    total_changes_found: Optional[int]
    significant_changes: Optional[List[dict]]

    # ==========================================
    # REPORT — from prepare_report
    # Formatted for Slack posting
    # ==========================================
    slack_report: Optional[str]
    report_summary: Optional[str]
    slack_channel: Optional[str]
    report_ready: Optional[bool]

    # ==========================================
    # METADATA
    # ==========================================
    request_id: Optional[str]
    error: Optional[str]
    completed: Optional[bool]