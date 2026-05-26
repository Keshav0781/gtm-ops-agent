"""
Node 2 — Analyze Deals

Second node in CRM Hygiene Agent.
Checks every deal against business rules
and categorises problems found.

This node uses NO LLM — pure Python logic.
Checking days since last contact is math.
Checking missing fields is string checking.
No intelligence needed — just rules.

Use LLM only where reasoning is needed.
Use Python for everything else.
Faster, cheaper, more predictable.

Business rules implemented:
STALE — no contact for 7+ days
STUCK — same stage for 14+ days  
INCOMPLETE — missing critical fields
MISSING VALUE — no deal value entered
"""

import logging
from datetime import datetime, date
from typing import List, Dict
from agents.crm_hygiene.state import CRMState

logger = logging.getLogger(__name__)

# ==========================================
# Business Rules Configuration
# ==========================================
STALE_DAYS_THRESHOLD = 7      # days without contact
STUCK_DAYS_THRESHOLD = 14     # days in same stage
REQUIRED_FIELDS = [
    "contact_email",
    "contact_phone",
    "deal_value",
    "owner"
]


def calculate_days_inactive(
    last_contact_date: str
) -> int:
    """
    Calculates how many days since last contact.
    Returns 0 if date is invalid or missing.
    """
    if not last_contact_date:
        return 999  # treat missing date as very stale

    try:
        last_contact = datetime.strptime(
            last_contact_date, "%Y-%m-%d"
        ).date()
        today = date.today()
        return (today - last_contact).days
    except ValueError:
        logger.warning(
            f"Invalid date format: {last_contact_date}"
        )
        return 999


def calculate_days_in_stage(
    stage_changed_date: str
) -> int:
    """
    Calculates how many days deal has been
    in current stage.
    """
    if not stage_changed_date:
        return 0

    try:
        stage_date = datetime.strptime(
            stage_changed_date, "%Y-%m-%d"
        ).date()
        today = date.today()
        return (today - stage_date).days
    except ValueError:
        return 0


def check_missing_fields(deal: Dict) -> List[str]:
    """
    Checks which required fields are missing
    or empty in a deal.
    Returns list of missing field names.
    """
    missing = []
    for field in REQUIRED_FIELDS:
        value = deal.get(field)
        if not value or str(value).strip() == "":
            missing.append(field)
    return missing


def analyze_deals(state: CRMState) -> CRMState:
    """
    Node 2 — Analyze all deals against rules.

    Not async — pure Python calculations.
    No LLM needed for rule-based analysis.

    What it does:
    1. Checks if Node 1 failed
    2. Analyzes each deal against business rules
    3. Categorises problems found
    4. Updates state with analysis results

    Input state fields used:
        raw_deals, scan_date

    Output state fields added:
        stale_deals, incomplete_deals,
        stuck_deals, healthy_deals_count,
        problematic_deals_count
    """

    # ==========================================
    # Step 1 — Check if previous node failed
    # ==========================================
    if state.get("error"):
        logger.warning(
            f"[{state.get('request_id')}] "
            f"Node 2: Skipping — previous node failed"
        )
        return state

    deals = state["raw_deals"]

    logger.info(
        f"[{state.get('request_id')}] "
        f"Node 2: Analyzing {len(deals)} deals"
    )

    stale_deals = []
    incomplete_deals = []
    stuck_deals = []
    healthy_count = 0

    # ==========================================
    # Step 2 — Check each deal against rules
    # ==========================================
    for deal in deals:
        problems_found = False

        # Check 1 — Stale deal
        days_inactive = calculate_days_inactive(
            deal.get("last_contact_date")
        )

        if days_inactive >= STALE_DAYS_THRESHOLD:
            stale_deals.append({
                **deal,
                "days_inactive": days_inactive,
                "alert_reason": (
                    f"No contact for {days_inactive} days"
                )
            })
            problems_found = True
            logger.debug(
                f"Stale deal: {deal.get('deal_name')} "
                f"— {days_inactive} days inactive"
            )

        # Check 2 — Incomplete deal
        missing_fields = check_missing_fields(deal)
        if missing_fields:
            incomplete_deals.append({
                **deal,
                "missing_fields": missing_fields,
                "alert_reason": (
                    f"Missing: {', '.join(missing_fields)}"
                )
            })
            problems_found = True
            logger.debug(
                f"Incomplete deal: {deal.get('deal_name')} "
                f"— missing {missing_fields}"
            )

        # Check 3 — Stuck deal
        days_in_stage = calculate_days_in_stage(
            deal.get("stage_changed_date")
        )

        if days_in_stage >= STUCK_DAYS_THRESHOLD:
            stuck_deals.append({
                **deal,
                "days_in_stage": days_in_stage,
                "alert_reason": (
                    f"Stuck in {deal.get('stage', 'unknown')} "
                    f"for {days_in_stage} days"
                )
            })
            problems_found = True
            logger.debug(
                f"Stuck deal: {deal.get('deal_name')} "
                f"— {days_in_stage} days in stage"
            )

        if not problems_found:
            healthy_count += 1

    # ==========================================
    # Step 3 — Update state with results
    # ==========================================
    state["stale_deals"] = stale_deals
    state["incomplete_deals"] = incomplete_deals
    state["stuck_deals"] = stuck_deals
    state["healthy_deals_count"] = healthy_count
    state["problematic_deals_count"] = (
        len(stale_deals) +
        len(incomplete_deals) +
        len(stuck_deals)
    )

    logger.info(
        f"[{state.get('request_id')}] "
        f"Node 2: Analysis complete — "
        f"stale={len(stale_deals)} "
        f"incomplete={len(incomplete_deals)} "
        f"stuck={len(stuck_deals)} "
        f"healthy={healthy_count}"
    )

    return state