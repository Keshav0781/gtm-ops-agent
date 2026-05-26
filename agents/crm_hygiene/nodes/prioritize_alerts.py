"""
Node 3 — Prioritize Alerts

Third node in CRM Hygiene Agent.
Takes analyzed deals and creates
structured alerts with priorities.

Combines stale, incomplete, and stuck deals
into single unified alert list.
Assigns priority based on severity.

No LLM needed — pure business logic.
Priority rules are deterministic.

"""

import logging
from typing import List
from agents.crm_hygiene.state import CRMState, DealAlert

logger = logging.getLogger(__name__)


def determine_priority(
    days_inactive: int = 0,
    missing_fields: List[str] = [],
    days_in_stage: int = 0,
    alert_type: str = "stale"
) -> str:
    """
    Determines alert priority based on severity.

    HIGH — needs attention today
    MEDIUM — needs attention this week
    LOW — minor issue, can wait
    """
    if alert_type == "stale":
        if days_inactive >= 21:
            return "HIGH"
        elif days_inactive >= 14:
            return "MEDIUM"
        return "LOW"

    if alert_type == "incomplete":
        critical_fields = ["contact_email", "contact_phone"]
        has_critical = any(
            f in missing_fields for f in critical_fields
        )
        if has_critical:
            return "HIGH"
        return "MEDIUM"

    if alert_type == "stuck":
        if days_in_stage >= 30:
            return "HIGH"
        elif days_in_stage >= 21:
            return "MEDIUM"
        return "LOW"

    return "LOW"


def format_slack_alert(
    deal: dict,
    alert_type: str,
    priority: str
) -> str:
    """
    Formats individual deal alert for Slack.
    Concise — one line per deal in owner message.
    """
    priority_emoji = {
        "HIGH": "🔴",
        "MEDIUM": "🟡",
        "LOW": "🟢"
    }
    emoji = priority_emoji.get(priority, "⚪")

    if alert_type == "stale":
        days = deal.get("days_inactive", 0)
        return (
            f"{emoji} *{deal.get('deal_name')}* "
            f"({deal.get('company', 'Unknown')}) — "
            f"No contact for *{days} days*. "
            f"Last stage: {deal.get('stage', 'Unknown')}"
        )

    if alert_type == "incomplete":
        missing = deal.get("missing_fields", [])
        return (
            f"{emoji} *{deal.get('deal_name')}* "
            f"({deal.get('company', 'Unknown')}) — "
            f"Missing: *{', '.join(missing)}*"
        )

    if alert_type == "stuck":
        days = deal.get("days_in_stage", 0)
        return (
            f"{emoji} *{deal.get('deal_name')}* "
            f"({deal.get('company', 'Unknown')}) — "
            f"Stuck in *{deal.get('stage', 'Unknown')}* "
            f"for *{days} days*"
        )

    return f"{emoji} *{deal.get('deal_name')}* — Review needed"


def prioritize_alerts(state: CRMState) -> CRMState:
    """
    Node 3 — Create prioritized alerts from analysis.

    Not async — pure Python logic.

    What it does:
    1. Checks if previous nodes failed
    2. Creates DealAlert for each problem found
    3. Assigns priority to each alert
    4. Sorts by priority — HIGH first
    5. Updates state with alerts

    Input state fields used:
        stale_deals, incomplete_deals, stuck_deals

    Output state fields added:
        alerts, high_priority_count,
        medium_priority_count, low_priority_count
    """

    # ==========================================
    # Step 1 — Check if previous nodes failed
    # ==========================================
    if state.get("error"):
        logger.warning(
            f"[{state.get('request_id')}] "
            f"Node 3: Skipping — previous node failed"
        )
        return state

    logger.info(
        f"[{state.get('request_id')}] "
        f"Node 3: Prioritizing alerts"
    )

    alerts = []

    # ==========================================
    # Step 2 — Create alerts for stale deals
    # ==========================================
    for deal in state.get("stale_deals", []):
        days_inactive = deal.get("days_inactive", 0)
        priority = determine_priority(
            days_inactive=days_inactive,
            alert_type="stale"
        )
        slack_message = format_slack_alert(
            deal, "stale", priority
        )
        alert: DealAlert = {
            "deal_id": deal.get("deal_id", ""),
            "deal_name": deal.get("deal_name", ""),
            "company": deal.get("company", "Unknown"),
            "owner": deal.get("owner", "Unassigned"),
            "alert_type": "stale",
            "priority": priority,
            "days_inactive": days_inactive,
            "missing_fields": None,
            "recommended_action": (
                f"Follow up with "
                f"{deal.get('company', 'customer')} — "
                f"last contact {days_inactive} days ago"
            ),
            "slack_message": slack_message
        }
        alerts.append(alert)

    # ==========================================
    # Step 3 — Create alerts for incomplete deals
    # ==========================================
    for deal in state.get("incomplete_deals", []):
        missing = deal.get("missing_fields", [])
        priority = determine_priority(
            missing_fields=missing,
            alert_type="incomplete"
        )
        slack_message = format_slack_alert(
            deal, "incomplete", priority
        )
        alert: DealAlert = {
            "deal_id": deal.get("deal_id", ""),
            "deal_name": deal.get("deal_name", ""),
            "company": deal.get("company", "Unknown"),
            "owner": deal.get("owner", "Unassigned"),
            "alert_type": "incomplete",
            "priority": priority,
            "days_inactive": None,
            "missing_fields": missing,
            "recommended_action": (
                f"Add missing information: "
                f"{', '.join(missing)}"
            ),
            "slack_message": slack_message
        }
        alerts.append(alert)

    # ==========================================
    # Step 4 — Create alerts for stuck deals
    # ==========================================
    for deal in state.get("stuck_deals", []):
        days_in_stage = deal.get("days_in_stage", 0)
        priority = determine_priority(
            days_in_stage=days_in_stage,
            alert_type="stuck"
        )
        slack_message = format_slack_alert(
            deal, "stuck", priority
        )
        alert: DealAlert = {
            "deal_id": deal.get("deal_id", ""),
            "deal_name": deal.get("deal_name", ""),
            "company": deal.get("company", "Unknown"),
            "owner": deal.get("owner", "Unassigned"),
            "alert_type": "stuck",
            "priority": priority,
            "days_inactive": None,
            "missing_fields": None,
            "recommended_action": (
                f"Review deal stage — stuck for "
                f"{days_in_stage} days"
            ),
            "slack_message": slack_message
        }
        alerts.append(alert)

    # ==========================================
    # Step 5 — Sort by priority HIGH first
    # ==========================================
    priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    alerts.sort(
        key=lambda x: priority_order.get(
            x["priority"], 3
        )
    )

    # ==========================================
    # Step 6 — Count by priority
    # ==========================================
    high_count = sum(
        1 for a in alerts if a["priority"] == "HIGH"
    )
    medium_count = sum(
        1 for a in alerts if a["priority"] == "MEDIUM"
    )
    low_count = sum(
        1 for a in alerts if a["priority"] == "LOW"
    )

    state["alerts"] = alerts
    state["high_priority_count"] = high_count
    state["medium_priority_count"] = medium_count
    state["low_priority_count"] = low_count

    logger.info(
        f"[{state.get('request_id')}] "
        f"Node 3: Prioritization complete — "
        f"HIGH={high_count} "
        f"MEDIUM={medium_count} "
        f"LOW={low_count}"
    )

    return state