"""
Email Triage Agent — State Definition

Shared notebook flowing through all 4 nodes.

Flow:
classify_email → extract_context → 
draft_reply → route_email

At Siemens similar state patterns are used
for clinical document routing workflows
where emails are replaced by patient referrals
and routing targets are clinical departments.
"""

from typing import Optional
from typing_extensions import TypedDict


class EmailState(TypedDict):
    """
    Complete state for Email Triage Agent.
    Each node reads from and adds to this state.
    """

    # ==========================================
    # INPUT — incoming email data
    # Set at entry point before graph runs
    # ==========================================
    sender_email: Optional[str]
    sender_name: Optional[str]
    subject: Optional[str]
    body: Optional[str]
    received_at: Optional[str]

    # ==========================================
    # CLASSIFICATION — from classify_email node
    # What type of email is this?
    # ==========================================
    classification: Optional[str]    # sales, support,
                                     # partnership, spam,
                                     # finance, press
    classification_reasoning: Optional[str]
    priority: Optional[str]          # high, medium, low
    sentiment: Optional[str]         # positive, neutral,
                                     # negative, urgent

    # ==========================================
    # CONTEXT — from extract_context node
    # What does sender need? Who are they?
    # ==========================================
    sender_company: Optional[str]
    sender_role: Optional[str]
    core_request: Optional[str]
    key_details: Optional[str]
    requires_immediate_action: Optional[bool]

    # ==========================================
    # REPLY — from draft_reply node
    # Appropriate response based on type
    # ==========================================
    draft_reply_subject: Optional[str]
    draft_reply_body: Optional[str]
    reply_tone: Optional[str]        # formal, friendly,
                                     # empathetic, brief

    # ==========================================
    # ROUTING — from route_email node
    # Who should handle this email?
    # ==========================================
    route_to: Optional[str]          # sales, support,
                                     # ceo, finance,
                                     # marketing, ignore
    route_reason: Optional[str]
    slack_channel: Optional[str]     # which Slack channel
                                     # to notify

    # ==========================================
    # METADATA — tracking and audit
    # Same pattern as Lead Intelligence Agent
    # ==========================================
    request_id: Optional[str]
    error: Optional[str]
    completed: Optional[bool]