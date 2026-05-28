"""
HR Onboarding Router

Two endpoints:
1. POST /hr/onboard — receives natural language request,
   plans provisioning, saves state to DB,
   sends approval card to Slack

2. POST /hr/provision — called by n8n after manager
   approves in Slack, retrieves state from DB,
   executes actual provisioning
"""

import logging
import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from agents.hr_onboarding.graph import (
    hr_onboarding_graph,
    hr_provisioning_graph
)
from api.database import (
    save_onboarding_state,
    get_onboarding_state,
    update_provisioning_status
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/hr",
    tags=["HR Onboarding"]
)


# ==========================================
# Request Models
# ==========================================
class HROnboardingRequest(BaseModel):
    """
    Natural language onboarding request from HR.
    """
    onboarding_request: str


class HRProvisionRequest(BaseModel):
    """
    Provision request from n8n after manager approves.
    Only needs request_id — full state retrieved from DB.
    """
    request_id: str


# ==========================================
# Response Model
# ==========================================
class HROnboardingResponse(BaseModel):
    """
    Agent result returned to caller.
    """
    request_id: str
    employee_name: Optional[str] = None
    employee_email: Optional[str] = None
    role: Optional[str] = None
    department: Optional[str] = None
    start_date: Optional[str] = None
    systems_to_provision: Optional[List[str]] = None
    slack_channels: Optional[List[str]] = None
    drive_folder_path: Optional[str] = None
    requires_github: Optional[bool] = None
    requires_figma: Optional[bool] = None
    provisioning_plan_summary: Optional[str] = None
    approval_message: Optional[str] = None
    approval_sent: Optional[bool] = None
    drive_folder_created: Optional[bool] = None
    drive_folder_url: Optional[str] = None
    calendar_shared: Optional[bool] = None
    slack_invited: Optional[bool] = None
    welcome_email_sent: Optional[bool] = None
    confirmation_sent: Optional[bool] = None
    error: Optional[str] = None
    completed: Optional[bool] = None


@router.post("/onboard", response_model=HROnboardingResponse)
async def onboard_employee(request: HROnboardingRequest):
    """
    Step 1 — Parse request, plan provisioning,
    save state to DB, send approval card to Slack.
    """

    request_id = str(uuid.uuid4())[:8]

    logger.info(
        f"[{request_id}] "
        f"HR onboarding request: "
        f"{request.onboarding_request[:50]}..."
    )

    initial_state = {
        "onboarding_request": request.onboarding_request,
        "request_id": request_id,
        "error": None,
        "completed": False
    }

    try:
        result = await hr_onboarding_graph.ainvoke(
            initial_state
        )

        # ==========================================
        # Save state to database
        # So /hr/provision can retrieve it later
        # using just the request_id
        # ==========================================
        await save_onboarding_state(result)

        logger.info(
            f"[{request_id}] "
            f"Onboarding plan complete — "
            f"employee={result.get('employee_name')} "
            f"approval_sent={result.get('approval_sent')}"
        )

        return HROnboardingResponse(
            request_id=request_id,
            employee_name=result.get("employee_name"),
            employee_email=result.get("employee_email"),
            role=result.get("role"),
            department=result.get("department"),
            start_date=result.get("start_date"),
            systems_to_provision=result.get(
                "systems_to_provision"
            ),
            slack_channels=result.get("slack_channels"),
            drive_folder_path=result.get("drive_folder_path"),
            requires_github=result.get("requires_github"),
            requires_figma=result.get("requires_figma"),
            provisioning_plan_summary=result.get(
                "provisioning_plan_summary"
            ),
            approval_message=result.get("approval_message"),
            approval_sent=result.get("approval_sent"),
            error=result.get("error"),
            completed=result.get("completed")
        )

    except Exception as e:
        logger.error(
            f"[{request_id}] "
            f"Onboarding failed — {str(e)}"
        )
        raise HTTPException(
            status_code=500,
            detail=f"Agent failed: {str(e)}"
        )


@router.post("/provision", response_model=HROnboardingResponse)
async def provision_employee(request: HRProvisionRequest):
    """
    Step 2 — Execute provisioning after manager approval.

    Called by n8n when manager types APPROVE in Slack.
    Retrieves full state from DB using request_id.
    Runs deploy_and_notify node.
    """

    logger.info(
        f"[{request.request_id}] "
        f"Provisioning request received"
    )

    # ==========================================
    # Retrieve state from database
    # ==========================================
    state = await get_onboarding_state(request.request_id)

    if not state:
        raise HTTPException(
            status_code=404,
            detail=f"No onboarding request found for "
                   f"request_id={request.request_id}"
        )

    logger.info(
        f"[{request.request_id}] "
        f"State retrieved for {state.get('employee_name')}"
    )

    try:
        result = await hr_provisioning_graph.ainvoke(state)

        # ==========================================
        # Update provisioning status in database
        # ==========================================
        await update_provisioning_status(
            request_id=request.request_id,
            slack_invited=result.get("slack_invited", False),
            welcome_email_sent=result.get(
                "welcome_email_sent", False
            ),
            confirmation_sent=result.get(
                "confirmation_sent", False
            )
        )

        logger.info(
            f"[{request.request_id}] "
            f"Provisioning complete"
        )

        return HROnboardingResponse(
            request_id=request.request_id,
            employee_name=result.get("employee_name"),
            employee_email=result.get("employee_email"),
            role=result.get("role"),
            department=result.get("department"),
            start_date=result.get("start_date"),
            systems_to_provision=result.get(
                "systems_to_provision"
            ),
            slack_channels=result.get("slack_channels"),
            drive_folder_path=result.get("drive_folder_path"),
            requires_github=result.get("requires_github"),
            requires_figma=result.get("requires_figma"),
            drive_folder_created=result.get(
                "drive_folder_created"
            ),
            drive_folder_url=result.get("drive_folder_url"),
            calendar_shared=result.get("calendar_shared"),
            slack_invited=result.get("slack_invited"),
            welcome_email_sent=result.get("welcome_email_sent"),
            confirmation_sent=result.get("confirmation_sent"),
            error=result.get("error"),
            completed=result.get("completed")
        )

    except Exception as e:
        logger.error(
            f"[{request.request_id}] "
            f"Provisioning failed — {str(e)}"
        )
        raise HTTPException(
            status_code=500,
            detail=f"Provisioning failed: {str(e)}"
        )