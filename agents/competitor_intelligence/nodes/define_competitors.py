"""
Node 1 — Define Competitors

First node in Competitor Intelligence Agent.
Validates competitor list and defines
which pages to check for each competitor.

Different competitor types need different pages:
SaaS company → homepage, pricing, blog, careers
Enterprise → homepage, products, news, careers
Marketplace → homepage, pricing, features

No LLM needed — pure validation and config.

"""

import logging
from typing import List
from agents.competitor_intelligence.state import (
    CompetitorState
)

logger = logging.getLogger(__name__)

# Default pages to check per competitor
# Can be customised per competitor in request
DEFAULT_PAGES = [
    "",           # homepage
    "/pricing",   # pricing page
    "/blog",      # blog/news
    "/careers"    # job postings signal growth
]


def build_pages_list(
    competitor: dict
) -> List[str]:
    """
    Builds list of pages to check for competitor.
    Uses custom pages if provided otherwise defaults.
    """
    custom_pages = competitor.get("pages")
    if custom_pages and isinstance(custom_pages, list):
        return custom_pages
    return DEFAULT_PAGES


def define_competitors(
    state: CompetitorState
) -> CompetitorState:
    """
    Node 1 — Validate and prepare competitor list.

    Not async — pure validation logic.

    What it does:
    1. Validates competitors list exists
    2. Validates each competitor has name and URL
    3. Builds pages list for each competitor
    4. Prepares structured competitor data
    5. Updates state

    Input state fields used:
        competitors, report_date

    Output state fields added:
        competitors (enriched with pages),
        report_date (if not provided)
    """

    # ==========================================
    # Step 1 — Validate competitors exist
    # ==========================================
    if not state.get("competitors"):
        logger.error(
            f"[{state.get('request_id')}] "
            f"Node 1: No competitors provided"
        )
        state["error"] = "No competitors provided"
        state["completed"] = False
        return state

    competitors = state["competitors"]
    valid_competitors = []

    # ==========================================
    # Step 2 — Validate each competitor
    # ==========================================
    for comp in competitors:
        if not comp.get("name") or not comp.get("url"):
            logger.warning(
                f"[{state.get('request_id')}] "
                f"Node 1: Skipping competitor — "
                f"missing name or URL"
            )
            continue

        url = comp["url"].rstrip("/")
        if not url.startswith("http"):
            url = f"https://{url}"

        enriched = {
            "name": comp["name"],
            "url": url,
            "pages_to_check": build_pages_list(comp),
            "current_content": None,
            "previous_content": comp.get(
                "previous_content", None
            ),
            "changes_detected": False,
            "changes_summary": None,
            "fetch_error": None
        }
        valid_competitors.append(enriched)

    if not valid_competitors:
        logger.error(
            f"[{state.get('request_id')}] "
            f"Node 1: No valid competitors found"
        )
        state["error"] = "No valid competitors found"
        state["completed"] = False
        return state

    # ==========================================
    # Step 3 — Set report date if not provided
    # ==========================================
    if not state.get("report_date"):
        from datetime import datetime
        state["report_date"] = datetime.now().strftime(
            "%Y-%m-%d"
        )

    state["competitors"] = valid_competitors

    logger.info(
        f"[{state.get('request_id')}] "
        f"Node 1: Defined {len(valid_competitors)} "
        f"competitors to monitor"
    )

    return state