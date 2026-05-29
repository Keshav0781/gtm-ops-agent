"""
Node 4 — Route Email

Final node in Email Triage Agent.
Decides which team member should handle
this email and which Slack channel to notify.

This node does NOT send anything.
It only decides routing and prepares
the Slack notification content.

Actual sending happens in n8n after
human approval — Phase 8.
"""

import logging
from agents.email_triage.state import EmailState

logger = logging.getLogger(__name__)

# ==========================================
# Routing Rules — Business Logic
# Defines who handles each email type
# In a real company this comes from config
# so it can be changed without code changes
# ==========================================
ROUTING_RULES = {
    "SALES": {
        "route_to": "sales",
        "slack_channel": "#sales-leads",
        "reason": "New potential customer inquiry"
    },
    "SUPPORT": {
        "route_to": "support",
        "slack_channel": "#customer-support",
        "reason": "Customer needs technical assistance"
    },
    "PARTNERSHIP": {
        "route_to": "ceo",
        "slack_channel": "#partnerships",
        "reason": "Partnership opportunity for leadership review"
    },
    "PRESS": {
        "route_to": "marketing",
        "slack_channel": "#press-inquiries",
        "reason": "Media inquiry requires PR handling"
    },
    "FINANCE": {
        "route_to": "finance",
        "slack_channel": "#finance",
        "reason": "Financial matter requires finance team"
    },
    "SPAM": {
        "route_to": "ignore",
        "slack_channel": None,
        "reason": "Classified as spam — no action needed"
    },
    "RECRUITING": {
        "route_to": "hr",
        "slack_channel": "#recruiting",
        "reason": "Job application requires HR team review"
    },
    "INVESTOR": {
        "route_to": "ceo",
        "slack_channel": "#investor-relations",
        "reason": "Investment inquiry requires CEO attention"
    }
}

# ==========================================
# Default fallback for any classification
# not in ROUTING_RULES above.
# Ensures no email is ever lost or silently
# misrouted regardless of what LLM returns.
# ==========================================
DEFAULT_ROUTING = {
    "route_to": "general",
    "slack_channel": "#general-inbox",
    "reason": "Unrecognised email type — requires manual review"
}


def route_email(state: EmailState) -> EmailState:
    """
    Node 4 — Determine email routing.

    Note: This node is NOT async.
    No LLM call needed — routing is
    rule-based, not LLM-based.

    Why rule-based here?
    Routing rules are business decisions
    that should be predictable and consistent.
    LLM introduces unnecessary variability
    for something that has clear rules.

    What it does:
    1. Checks if previous nodes failed
    2. Looks up routing rules for classification
    3. Falls back to general inbox for unknown types
    4. Adjusts routing for HIGH priority emails
    5. Updates state with routing decision

    Input state fields used:
        classification, priority,
        requires_immediate_action,
        sender_name, sender_company,
        core_request

    Output state fields added:
        route_to, route_reason,
        slack_channel, completed
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

    classification = state.get("classification", "UNKNOWN")
    priority = state.get("priority", "MEDIUM")
    requires_immediate = state.get(
        "requires_immediate_action", False
    )

    logger.info(
        f"[{state.get('request_id')}] "
        f"Node 4: Routing {classification} email "
        f"priority={priority}"
    )

    # ==========================================
    # Step 2 — Apply routing rules
    # Falls back to DEFAULT_ROUTING for any
    # classification not in ROUTING_RULES
    # ==========================================
    routing = ROUTING_RULES.get(classification, DEFAULT_ROUTING)

    state["route_to"] = routing["route_to"]
    state["slack_channel"] = routing["slack_channel"]
    state["route_reason"] = routing["reason"]

    # ==========================================
    # Step 3 — Escalate HIGH priority emails
    # If HIGH priority and requires immediate
    # action — flag urgently
    # ==========================================
    if priority == "HIGH" and requires_immediate:
        logger.warning(
            f"[{state.get('request_id')}] "
            f"Node 4: URGENT email detected — "
            f"escalating to management"
        )
        state["route_reason"] = (
            f"URGENT — {routing['reason']} "
            f"Requires immediate attention"
        )

    # ==========================================
    # Step 4 — Mark as completed
    # ==========================================
    state["completed"] = True

    logger.info(
        f"[{state.get('request_id')}] "
        f"Node 4: Routing complete — "
        f"route_to={state['route_to']} "
        f"channel={state['slack_channel']}"
    )

    return state
