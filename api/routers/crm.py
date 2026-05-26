"""
CRM Hygiene Router

FastAPI router exposing CRM Hygiene Agent
as a REST endpoint.

Called by:
- n8n scheduler every morning at 9am
- Dashboard when running manual scan
- Testing manually via curl

"""

import logging
import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict
from agents.crm_hygiene.graph import crm_hygiene_graph

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/crm",
    tags=["CRM Hygiene"]
)


class DealInput(BaseModel):
    """
    Single deal from CRM system.
    In production comes from HubSpot API.
    For testing provide realistic fake data.
    """
    deal_id: str
    deal_name: str
    company: str
    owner: str
    stage: Optional[str] = None
    deal_value: Optional[float] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    last_contact_date: Optional[str] = None
    stage_changed_date: Optional[str] = None


class CRMRequest(BaseModel):
    """
    Request body containing all deals to scan.
    """
    deals: List[DealInput]
    scan_date: Optional[str] = None


class CRMResponse(BaseModel):
    """
    Agent result with all alerts and notifications.
    """
    request_id: str
    scan_date: Optional[str] = None
    total_deals_count: Optional[int] = None
    healthy_deals_count: Optional[int] = None
    problematic_deals_count: Optional[int] = None
    total_alerts_count: Optional[int] = None
    high_priority_count: Optional[int] = None
    medium_priority_count: Optional[int] = None
    low_priority_count: Optional[int] = None
    owner_notifications: Optional[Dict] = None
    scan_summary: Optional[str] = None
    error: Optional[str] = None
    completed: Optional[bool] = None


@router.post("/analyze", response_model=CRMResponse)
async def analyze_crm(request: CRMRequest):
    """
    Run CRM hygiene scan on provided deals.

    Flow:
    1. Generate unique request ID
    2. Convert deals to raw format
    3. Run agent graph
    4. Return alerts grouped by owner
    """

    request_id = str(uuid.uuid4())[:8]

    logger.info(
        f"[{request_id}] "
        f"CRM scan started — "
        f"{len(request.deals)} deals"
    )

    raw_deals = [
        deal.model_dump() for deal in request.deals
    ]

    initial_state = {
        "raw_deals": raw_deals,
        "scan_date": request.scan_date,
        "request_id": request_id,
        "error": None,
        "completed": False
    }

    try:
        result = await crm_hygiene_graph.ainvoke(
            initial_state
        )

        logger.info(
            f"[{request_id}] "
            f"CRM scan complete — "
            f"alerts={result.get('total_alerts_count')}"
        )

        return CRMResponse(
            request_id=request_id,
            scan_date=result.get("scan_date"),
            total_deals_count=result.get(
                "total_deals_count"
            ),
            healthy_deals_count=result.get(
                "healthy_deals_count"
            ),
            problematic_deals_count=result.get(
                "problematic_deals_count"
            ),
            total_alerts_count=result.get(
                "total_alerts_count"
            ),
            high_priority_count=result.get(
                "high_priority_count"
            ),
            medium_priority_count=result.get(
                "medium_priority_count"
            ),
            low_priority_count=result.get(
                "low_priority_count"
            ),
            owner_notifications=result.get(
                "owner_notifications"
            ),
            scan_summary=result.get("scan_summary"),
            error=result.get("error"),
            completed=result.get("completed")
        )

    except Exception as e:
        logger.error(
            f"[{request_id}] "
            f"CRM scan failed — {str(e)}"
        )
        raise HTTPException(
            status_code=500,
            detail=f"Agent failed: {str(e)}"
        )