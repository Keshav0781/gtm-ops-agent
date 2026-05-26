"""
Meeting Intelligence Router

FastAPI router exposing Meeting Intelligence
Agent as a REST endpoint.

Receives meeting data → runs agent → returns result.

Called by:
- n8n when Google Calendar detects meeting ended
- Google Drive MCP fetches transcript automatically
- Dashboard when testing manually
"""

import logging
import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from agents.meeting_intelligence.graph import (
    meeting_intelligence_graph
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/meetings",
    tags=["Meeting Intelligence"]
)


# ==========================================
# Request Model
# ==========================================
class MeetingRequest(BaseModel):
    """
    Incoming meeting data.
    In Phase 8 transcript comes automatically
    from Google Drive MCP after meeting ends.
    """
    meeting_title: Optional[str] = "Team Meeting"
    meeting_date: Optional[str] = None
    attendees: Optional[str] = None
    transcript: str
    duration_minutes: Optional[int] = None


# ==========================================
# Response Model
# ==========================================
class MeetingResponse(BaseModel):
    """
    Agent result returned to caller.
    Contains everything needed for
    Slack notification and Notion tasks.
    """
    request_id: str
    meeting_title: Optional[str] = None
    meeting_type: Optional[str] = None
    topics_discussed: Optional[str] = None
    participants_identified: Optional[str] = None
    action_items_count: Optional[int] = None
    decisions_made: Optional[str] = None
    blockers_identified: Optional[str] = None
    summary: Optional[str] = None
    key_outcomes: Optional[str] = None
    next_meeting_suggested: Optional[str] = None
    slack_message: Optional[str] = None
    slack_channel: Optional[str] = None
    notion_tasks_payload: Optional[str] = None
    notifications_ready: Optional[bool] = None
    error: Optional[str] = None
    completed: Optional[bool] = None


@router.post("/analyze", response_model=MeetingResponse)
async def analyze_meeting(meeting: MeetingRequest):
    """
    Analyze meeting transcript using
    Meeting Intelligence Agent.

    Flow:
    1. Generate unique request ID
    2. Build initial state
    3. Run agent graph
    4. Return result with Slack and Notion payloads
    """

    # ==========================================
    # Step 1 — Generate request ID
    # ==========================================
    request_id = str(uuid.uuid4())[:8]

    logger.info(
        f"[{request_id}] "
        f"New meeting received: "
        f"{meeting.meeting_title}"
    )

    # ==========================================
    # Step 2 — Build initial state
    # ==========================================
    initial_state = {
        "meeting_title": meeting.meeting_title,
        "meeting_date": meeting.meeting_date,
        "attendees": meeting.attendees,
        "transcript": meeting.transcript,
        "duration_minutes": meeting.duration_minutes,
        "request_id": request_id,
        "error": None,
        "completed": False
    }

    # ==========================================
    # Step 3 — Run agent graph
    # ==========================================
    try:
        result = await meeting_intelligence_graph.ainvoke(
            initial_state
        )

        logger.info(
            f"[{request_id}] "
            f"Meeting analysis complete — "
            f"type={result.get('meeting_type')} "
            f"actions={result.get('action_items_count')}"
        )

        # ==========================================
        # Step 4 — Return result
        # ==========================================
        return MeetingResponse(
            request_id=request_id,
            meeting_title=result.get("meeting_title"),
            meeting_type=result.get("meeting_type"),
            topics_discussed=result.get("topics_discussed"),
            participants_identified=result.get(
                "participants_identified"
            ),
            action_items_count=result.get("action_items_count"),
            decisions_made=result.get("decisions_made"),
            blockers_identified=result.get("blockers_identified"),
            summary=result.get("summary"),
            key_outcomes=result.get("key_outcomes"),
            next_meeting_suggested=result.get(
                "next_meeting_suggested"
            ),
            slack_message=result.get("slack_message"),
            slack_channel=result.get("slack_channel"),
            notion_tasks_payload=result.get(
                "notion_tasks_payload"
            ),
            notifications_ready=result.get("notifications_ready"),
            error=result.get("error"),
            completed=result.get("completed")
        )

    except Exception as e:
        logger.error(
            f"[{request_id}] "
            f"Meeting analysis failed — {str(e)}"
        )
        raise HTTPException(
            status_code=500,
            detail=f"Agent failed: {str(e)}"
        )