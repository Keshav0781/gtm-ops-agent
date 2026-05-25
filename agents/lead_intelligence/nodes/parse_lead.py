"""
Node 1 — Parse Lead

First node in Lead Intelligence Agent.
Receives raw lead data and prepares it
for the next node (research_company).

Think of this as the receptionist:
- Receives incoming lead
- Cleans and validates data
- Passes to researcher
"""

import logging
from agents.lead_intelligence.state import LeadState

logger = logging.getLogger(__name__)


def parse_lead(state: LeadState) -> LeadState:
    """
    Node 1 — Parse and validate incoming lead data.
    
    What it does:
    1. Reads raw lead data from state
    2. Cleans whitespace and formatting
    3. Checks required fields exist
    4. Sets error if something critical is missing
    5. Returns updated state
    
    Input state fields used:
        company_name, contact_name, 
        contact_email, message
    
    Output state fields added:
        source, error (if validation fails)
    """
    logger.info(
        f"[{state.get('request_id')}] "
        f"Node 1: Parsing lead for "
        f"{state.get('company_name', 'Unknown')}"
    )

    # ==========================================
    # Step 1 — Clean incoming data
    # Strip whitespace from all string fields
    # Real leads often have extra spaces
    # ==========================================
    if state.get("company_name"):
        state["company_name"] = state["company_name"].strip()

    if state.get("contact_name"):
        state["contact_name"] = state["contact_name"].strip()

    if state.get("contact_email"):
        state["contact_email"] = state["contact_email"].strip().lower()

    if state.get("message"):
        state["message"] = state["message"].strip()

    # ==========================================
    # Step 2 — Validate required fields
    # company_name is the only truly required field
    # Cannot research a company without a name
    # ==========================================
    if not state.get("company_name"):
        logger.error(
            f"[{state.get('request_id')}] "
            f"Parse failed — company_name is missing"
        )
        state["error"] = "company_name is required"
        state["completed"] = False
        return state

    # ==========================================
    # Step 3 — Set default source if not provided
    # Helps track where leads come from
    # ==========================================
    if not state.get("source"):
        state["source"] = "website"

    logger.info(
        f"[{state.get('request_id')}] "
        f"Node 1: Parse complete — "
        f"company={state['company_name']} "
        f"email={state.get('contact_email', 'not provided')}"
    )

    return state