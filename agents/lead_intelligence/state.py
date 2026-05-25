"""
Lead Intelligence Agent — State Definition

This is the shared notebook that flows through
all 4 nodes of the Lead Intelligence Agent.

Each node reads from this state and adds to it.
Nothing is lost between nodes.


"""

from typing import Optional
from typing_extensions import TypedDict


class LeadState(TypedDict):
    """
    Complete state for Lead Intelligence Agent.
    
    Flows through nodes in this order:
    parse_lead → research_company → 
    score_lead → draft_email
    
    Each node adds its output to this state.
    """

    # ==========================================
    # INPUT — from incoming lead form
    # Set by parse_lead node
    # ==========================================
    company_name: str
    contact_name: Optional[str]
    contact_email: Optional[str]
    message: Optional[str]
    source: Optional[str]      # website, linkedin, referral

    # ==========================================
    # RESEARCH — from web search
    # Set by research_company node
    # ==========================================
    company_size: Optional[str]
    industry: Optional[str]
    company_description: Optional[str]
    company_website: Optional[str]
    research_summary: Optional[str]
    research_completed: Optional[bool]

    # ==========================================
    # SCORING — lead qualification
    # Set by score_lead node
    # ==========================================
    score: Optional[str]           # HIGH, MEDIUM, LOW
    score_reasoning: Optional[str]
    is_qualified: Optional[bool]

    # ==========================================
    # EMAIL — outbound draft
    # Set by draft_email node
    # Only created if score is HIGH or MEDIUM
    # ==========================================
    draft_email_subject: Optional[str]
    draft_email_body: Optional[str]
    email_tone: Optional[str]      # formal, casual

    # ==========================================
    # METADATA — tracking and audit
    # ==========================================
    request_id: Optional[str]
    error: Optional[str]           # captures any errors
    completed: Optional[bool]