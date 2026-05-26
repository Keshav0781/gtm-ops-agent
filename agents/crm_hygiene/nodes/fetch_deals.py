"""
Node 1 — Fetch Deals

First node in CRM Hygiene Agent.
Fetches all open deals from HubSpot
and prepares them for analysis.

In production — connects to real HubSpot API
using HUBSPOT_API_KEY from .env file.

For our project — accepts deals data directly
in request body. Same agent logic either way.
This pattern is called dependency injection —
easy to swap data source without changing
agent logic.


Business value:
Agent knows exactly which deals exist
and their current status before any
analysis begins.
"""

import logging
from datetime import datetime
from agents.crm_hygiene.state import CRMState

logger = logging.getLogger(__name__)


def fetch_deals(state: CRMState) -> CRMState:
    """
    Node 1 — Fetch and validate deals data.

    Note: This node is NOT async.
    No external API call in our version —
    data comes directly from request body.
    Pure data validation and preparation.

    In production async version would:
    1. Call HubSpot API with API key
    2. Paginate through all open deals
    3. Transform to our standard format

    What it does now:
    1. Validates deals data exists
    2. Validates each deal has required fields
    3. Adds scan metadata
    4. Updates state with validated deals

    Input state fields used:
        raw_deals, scan_date

    Output state fields added:
        total_deals_count, scan_date
    """

    # ==========================================
    # Step 1 — Validate deals data exists
    # ==========================================
    if not state.get("raw_deals"):
        logger.error(
            f"[{state.get('request_id')}] "
            f"Node 1: No deals data provided"
        )
        state["error"] = "No deals data provided"
        state["completed"] = False
        return state

    raw_deals = state["raw_deals"]

    logger.info(
        f"[{state.get('request_id')}] "
        f"Node 1: Fetching {len(raw_deals)} deals"
    )

    # ==========================================
    # Step 2 — Validate each deal has minimum
    # required fields
    # ==========================================
    valid_deals = []
    for deal in raw_deals:
        if not deal.get("deal_id") or \
           not deal.get("deal_name"):
            logger.warning(
                f"[{state.get('request_id')}] "
                f"Node 1: Skipping invalid deal — "
                f"missing required fields"
            )
            continue
        valid_deals.append(deal)

    if not valid_deals:
        logger.error(
            f"[{state.get('request_id')}] "
            f"Node 1: No valid deals found"
        )
        state["error"] = "No valid deals found"
        state["completed"] = False
        return state

    # ==========================================
    # Step 3 — Set scan metadata
    # ==========================================
    state["raw_deals"] = valid_deals
    state["total_deals_count"] = len(valid_deals)

    if not state.get("scan_date"):
        state["scan_date"] = datetime.now().strftime(
            "%Y-%m-%d"
        )

    logger.info(
        f"[{state.get('request_id')}] "
        f"Node 1: Fetch complete — "
        f"{state['total_deals_count']} valid deals"
    )

    return state