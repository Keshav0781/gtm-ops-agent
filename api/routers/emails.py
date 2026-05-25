"""
Email Triage Router

FastAPI router exposing Email Triage Agent
as a REST endpoint.

Receives email data → runs agent → returns result.

Called by:
- n8n when new email arrives in Gmail inbox
- Dashboard when testing manually

At Siemens every AI agent is exposed through
dedicated FastAPI routers — same pattern
across entire platform.
"""

import logging
import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from agents.email_triage.graph import email_triage_graph

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/emails",
    tags=["Email Triage"]
)


# ==========================================
# Request Model
# ==========================================
class EmailRequest(BaseModel):
    """
    Incoming email data.
    Mirrors what Gmail MCP will send
    when connected in Phase 8.
    """
    sender_email: str
    sender_name: Optional[str] = None
    subject: Optional[str] = None
    body: str
    received_at: Optional[str] = None


# ==========================================
# Response Model
# ==========================================
class EmailResponse(BaseModel):
    """
    Agent result returned to caller.
    Contains everything dashboard needs
    to show approval card.
    """
    request_id: str
    sender_email: str
    classification: Optional[str] = None
    classification_reasoning: Optional[str] = None
    priority: Optional[str] = None
    sentiment: Optional[str] = None
    sender_company: Optional[str] = None
    core_request: Optional[str] = None
    requires_immediate_action: Optional[bool] = None
    draft_reply_subject: Optional[str] = None
    draft_reply_body: Optional[str] = None
    route_to: Optional[str] = None
    slack_channel: Optional[str] = None
    route_reason: Optional[str] = None
    error: Optional[str] = None
    completed: Optional[bool] = None


@router.post("/triage", response_model=EmailResponse)
async def triage_email(email: EmailRequest):
    """
    Triage incoming email using Email Triage Agent.

    Flow:
    1. Generate unique request ID
    2. Build initial state
    3. Run agent graph
    4. Return result
    """

    # ==========================================
    # Step 1 — Generate request ID
    # ==========================================
    request_id = str(uuid.uuid4())[:8]

    logger.info(
        f"[{request_id}] "
        f"New email received from "
        f"{email.sender_email}"
    )

    # ==========================================
    # Step 2 — Build initial state
    # ==========================================
    initial_state = {
        "sender_email": email.sender_email,
        "sender_name": email.sender_name,
        "subject": email.subject,
        "body": email.body,
        "received_at": email.received_at,
        "request_id": request_id,
        "error": None,
        "completed": False
    }

    # ==========================================
    # Step 3 — Run agent graph
    # ==========================================
    try:
        result = await email_triage_graph.ainvoke(
            initial_state
        )

        logger.info(
            f"[{request_id}] "
            f"Email triage complete — "
            f"classification={result.get('classification')} "
            f"route_to={result.get('route_to')}"
        )

        # ==========================================
        # Step 4 — Return result
        # ==========================================
        return EmailResponse(
            request_id=request_id,
            sender_email=result.get("sender_email", ""),
            classification=result.get("classification"),
            classification_reasoning=result.get(
                "classification_reasoning"
            ),
            priority=result.get("priority"),
            sentiment=result.get("sentiment"),
            sender_company=result.get("sender_company"),
            core_request=result.get("core_request"),
            requires_immediate_action=result.get(
                "requires_immediate_action"
            ),
            draft_reply_subject=result.get(
                "draft_reply_subject"
            ),
            draft_reply_body=result.get("draft_reply_body"),
            route_to=result.get("route_to"),
            slack_channel=result.get("slack_channel"),
            route_reason=result.get("route_reason"),
            error=result.get("error"),
            completed=result.get("completed")
        )

    except Exception as e:
        logger.error(
            f"[{request_id}] "
            f"Email triage failed — {str(e)}"
        )
        raise HTTPException(
            status_code=500,
            detail=f"Agent failed: {str(e)}"
        )