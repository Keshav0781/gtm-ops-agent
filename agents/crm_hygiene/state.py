"""
CRM Hygiene Agent — State Definition

Shared notebook flowing through all 4 nodes.

Flow:
fetch_deals → analyze_deals → 
prioritize_alerts → prepare_alerts

Unlike other agents — this agent fetches
its own data. No user provides input.
n8n scheduler triggers it daily at 9am.

Real scenario:
Sales team has 30 open deals.
Agent runs at 9am every morning.
By 9:05am every deal owner has received
personalised Slack alert about their
stale or incomplete deals.
Zero manual checking required.
"""

from typing import Optional, List
from typing_extensions import TypedDict


class DealAlert(TypedDict):
    """
    Single deal alert ready for Slack notification.
    One alert per problematic deal.
    """
    deal_id: str
    deal_name: str
    company: str
    owner: str
    alert_type: str        # stale, incomplete,
                           # stuck, missing_value
    priority: str          # HIGH, MEDIUM, LOW
    days_inactive: Optional[int]
    missing_fields: Optional[List[str]]
    recommended_action: str
    slack_message: str


class CRMState(TypedDict):
    """
    Complete state for CRM Hygiene Agent.
    Each node reads from and adds to this state.
    """

    # ==========================================
    # INPUT — raw deals data
    # In production comes from HubSpot API
    # For our project comes from request body
    # Same agent logic regardless of source
    # ==========================================
    raw_deals: Optional[List[dict]]
    total_deals_count: Optional[int]
    scan_date: Optional[str]

    # ==========================================
    # ANALYSIS — from analyze_deals node
    # Results of checking each deal
    # ==========================================
    stale_deals: Optional[List[dict]]
    incomplete_deals: Optional[List[dict]]
    stuck_deals: Optional[List[dict]]
    healthy_deals_count: Optional[int]
    problematic_deals_count: Optional[int]

    # ==========================================
    # ALERTS — from prioritize_alerts node
    # Structured alerts ready for formatting
    # ==========================================
    alerts: Optional[List[DealAlert]]
    high_priority_count: Optional[int]
    medium_priority_count: Optional[int]
    low_priority_count: Optional[int]

    # ==========================================
    # NOTIFICATIONS — from prepare_alerts node
    # Grouped by owner for Slack delivery
    # One message per owner not per deal
    # ==========================================
    owner_notifications: Optional[dict]
    total_alerts_count: Optional[int]
    scan_summary: Optional[str]

    # ==========================================
    # METADATA — tracking and audit
    # ==========================================
    request_id: Optional[str]
    error: Optional[str]
    completed: Optional[bool]