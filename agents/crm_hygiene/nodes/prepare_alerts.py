"""
Node 4 — Prepare Alerts

Final node in CRM Hygiene Agent.
Groups alerts by deal owner and formats
one Slack message per owner.

Why one message per owner not per deal?
If John owns 5 stale deals — sending 5
separate Slack messages is annoying.
One consolidated message is professional.

No LLM needed — pure formatting logic.
Same reasoning as route_email and
prepare_notifications nodes.

"""

import logging
from typing import Dict, List
from agents.crm_hygiene.state import CRMState, DealAlert

logger = logging.getLogger(__name__)


def group_alerts_by_owner(
    alerts: List[DealAlert]
) -> Dict[str, List[DealAlert]]:
    """
    Groups all alerts by deal owner.
    Each owner gets their own group of alerts.
    """
    grouped = {}
    for alert in alerts:
        owner = alert.get("owner", "Unassigned")
        if owner not in grouped:
            grouped[owner] = []
        grouped[owner].append(alert)
    return grouped


def format_owner_message(
    owner: str,
    alerts: List[DealAlert],
    scan_date: str
) -> str:
    """
    Formats consolidated Slack message for one owner.
    Groups HIGH priority alerts first.
    """
    high_alerts = [
        a for a in alerts if a["priority"] == "HIGH"
    ]
    medium_alerts = [
        a for a in alerts if a["priority"] == "MEDIUM"
    ]
    low_alerts = [
        a for a in alerts if a["priority"] == "LOW"
    ]

    message = (
        f"*CRM Daily Digest — {scan_date}*\n"
        f"Hi {owner}, you have "
        f"*{len(alerts)} deal(s)* needing attention:\n\n"
    )

    if high_alerts:
        message += "*Urgent — Action Today:*\n"
        for alert in high_alerts:
            message += f"{alert['slack_message']}\n"
        message += "\n"

    if medium_alerts:
        message += "*This Week:*\n"
        for alert in medium_alerts:
            message += f"{alert['slack_message']}\n"
        message += "\n"

    if low_alerts:
        message += "*When You Get A Chance:*\n"
        for alert in low_alerts:
            message += f"{alert['slack_message']}\n"
        message += "\n"

    message += (
        f"_Reply to this message or visit "
        f"HubSpot to take action._"
    )

    return message.strip()


def prepare_alerts(state: CRMState) -> CRMState:
    """
    Node 4 — Prepare consolidated owner notifications.

    Not async — pure formatting logic.

    What it does:
    1. Checks if previous nodes failed
    2. Groups alerts by deal owner
    3. Formats one message per owner
    4. Creates scan summary
    5. Marks agent as completed

    Input state fields used:
        alerts, total_deals_count,
        healthy_deals_count, scan_date,
        high_priority_count, medium_priority_count,
        low_priority_count

    Output state fields added:
        owner_notifications, total_alerts_count,
        scan_summary, completed
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

    alerts = state.get("alerts", [])
    scan_date = state.get("scan_date", "Today")

    logger.info(
        f"[{state.get('request_id')}] "
        f"Node 4: Preparing alerts for "
        f"{len(alerts)} issues"
    )

    # ==========================================
    # Step 2 — Handle no alerts case
    # All deals healthy — still send summary
    # ==========================================
    if not alerts:
        state["owner_notifications"] = {}
        state["total_alerts_count"] = 0
        state["scan_summary"] = (
            f"CRM scan complete — {scan_date}. "
            f"All {state.get('total_deals_count', 0)} "
            f"deals healthy. No action needed."
        )
        state["completed"] = True
        logger.info(
            f"[{state.get('request_id')}] "
            f"Node 4: All deals healthy — no alerts"
        )
        return state

    # ==========================================
    # Step 3 — Group alerts by owner
    # ==========================================
    grouped = group_alerts_by_owner(alerts)

    # ==========================================
    # Step 4 — Format message per owner
    # ==========================================
    owner_notifications = {}
    for owner, owner_alerts in grouped.items():
        owner_notifications[owner] = {
            "message": format_owner_message(
                owner, owner_alerts, scan_date
            ),
            "alert_count": len(owner_alerts),
            "high_count": sum(
                1 for a in owner_alerts
                if a["priority"] == "HIGH"
            ),
            "alerts": owner_alerts
        }

    # ==========================================
    # Step 5 — Create scan summary
    # ==========================================
    total_deals = state.get("total_deals_count", 0)
    healthy = state.get("healthy_deals_count", 0)
    high = state.get("high_priority_count", 0)
    medium = state.get("medium_priority_count", 0)
    low = state.get("low_priority_count", 0)

    state["scan_summary"] = (
        f"CRM scan complete — {scan_date}. "
        f"Scanned {total_deals} deals. "
        f"Healthy: {healthy}. "
        f"Alerts: {high} urgent, "
        f"{medium} this week, "
        f"{low} low priority. "
        f"Notifying {len(grouped)} owner(s)."
    )

    state["owner_notifications"] = owner_notifications
    state["total_alerts_count"] = len(alerts)
    state["completed"] = True

    logger.info(
        f"[{state.get('request_id')}] "
        f"Node 4: Alerts ready — "
        f"{len(grouped)} owners to notify"
    )

    return state