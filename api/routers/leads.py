"""
Lead Intelligence Router

FastAPI router that exposes the Lead Intelligence
Agent as a REST endpoint.

Receives lead data → runs agent → returns result.
"""

import logging
import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from agents.lead_intelligence.graph import (
    lead_intelligence_graph
)

logger = logging.getLogger(__name__)

# Create router
# prefix means all endpoints start with /leads
router = APIRouter(prefix="/leads", tags=["Lead Intelligence"])


# ==========================================
# Request Model
# Defines exactly what data we expect
# Pydantic validates automatically
# Wrong data type → clear error message
# At Siemens all API inputs are strictly typed
# ==========================================
class LeadRequest(BaseModel):
    """
    Incoming lead data from contact form.
    Only company_name is required.
    Everything else is optional.
    """
    company_name: str
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    message: Optional[str] = None
    source: Optional[str] = "website"


# ==========================================
# Response Model
# Defines exactly what we return
# Clear contract between API and caller
# ==========================================
class LeadResponse(BaseModel):
    """
    Agent result returned to caller.
    Contains everything the dashboard
    needs to show the approval card.
    """
    request_id: str
    company_name: str
    score: Optional[str] = None
    score_reasoning: Optional[str] = None
    is_qualified: Optional[bool] = None
    industry: Optional[str] = None
    company_size: Optional[str] = None
    research_summary: Optional[str] = None
    draft_email_subject: Optional[str] = None
    draft_email_body: Optional[str] = None
    error: Optional[str] = None
    completed: Optional[bool] = None


@router.post("/analyze", response_model=LeadResponse)
async def analyze_lead(lead: LeadRequest):
    """
    Analyze incoming lead using Lead Intelligence Agent.

    Flow:
    1. Generate unique request ID
    2. Build initial state
    3. Run agent graph
    4. Return result

    Called by:
    - n8n when new lead form is submitted
    - Dashboard when testing manually
    """

    # ==========================================
    # Step 1 — Generate request ID
    # Same ID used throughout entire flow
    # Connects API log → agent log → database
    # ==========================================
    request_id = str(uuid.uuid4())[:8]

    logger.info(
        f"[{request_id}] "
        f"New lead received: {lead.company_name}"
    )

    # ==========================================
    # Step 2 — Build initial state
    # This is what gets passed to parse_lead
    # first node in our graph
    # ==========================================
    initial_state = {
        "company_name": lead.company_name,
        "contact_name": lead.contact_name,
        "contact_email": lead.contact_email,
        "message": lead.message,
        "source": lead.source,
        "request_id": request_id,
        "error": None,
        "completed": False
    }

    # ==========================================
    # Step 3 — Run the agent graph
    # ==========================================
    try:
        result = await lead_intelligence_graph.ainvoke(
            initial_state
        )

        logger.info(
            f"[{request_id}] "
            f"Lead analysis complete — "
            f"score={result.get('score')} "
            f"qualified={result.get('is_qualified')}"
        )

        # ==========================================
        # Step 4 — Return result
        # ==========================================
        return LeadResponse(
            request_id=request_id,
            company_name=result.get("company_name", ""),
            score=result.get("score"),
            score_reasoning=result.get("score_reasoning"),
            is_qualified=result.get("is_qualified"),
            industry=result.get("industry"),
            company_size=result.get("company_size"),
            research_summary=result.get("research_summary"),
            draft_email_subject=result.get(
                "draft_email_subject"
            ),
            draft_email_body=result.get("draft_email_body"),
            error=result.get("error"),
            completed=result.get("completed")
        )

    except Exception as e:
        logger.error(
            f"[{request_id}] "
            f"Lead analysis failed — {str(e)}"
        )
        raise HTTPException(
            status_code=500,
            detail=f"Agent failed: {str(e)}"
        )