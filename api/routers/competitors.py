"""
Competitor Intelligence Router

FastAPI router exposing Competitor Intelligence
Agent as a REST endpoint.

Called by:
- n8n scheduler every Monday morning
- Dashboard when running manual scan
- Testing manually via curl

Note: This endpoint takes longer than others
due to real HTTP requests to competitor sites.
Typical response time: 30-120 seconds
depending on number of competitors and pages.

"""

import logging
import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict
from agents.competitor_intelligence.graph import (
    competitor_intelligence_graph
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/competitors",
    tags=["Competitor Intelligence"]
)


class CompetitorInput(BaseModel):
    """
    Single competitor to monitor.
    """
    name: str
    url: str
    pages: Optional[List[str]] = None
    previous_content: Optional[Dict] = None


class CompetitorRequest(BaseModel):
    """
    Request body with list of competitors to monitor.
    """
    competitors: List[CompetitorInput]
    report_date: Optional[str] = None


class CompetitorResponse(BaseModel):
    """
    Agent result with competitive intelligence report.
    """
    request_id: str
    report_date: Optional[str] = None
    successful_scrapes: Optional[int] = None
    failed_scrapes: Optional[int] = None
    total_changes_found: Optional[int] = None
    competitor_analyses: Optional[List[Dict]] = None
    slack_report: Optional[str] = None
    report_summary: Optional[str] = None
    slack_channel: Optional[str] = None
    report_ready: Optional[bool] = None
    error: Optional[str] = None
    completed: Optional[bool] = None


@router.post("/analyze", response_model=CompetitorResponse)
async def analyze_competitors(
    request: CompetitorRequest
):
    """
    Run competitive intelligence scan.

    Flow:
    1. Generate unique request ID
    2. Build initial state
    3. Run agent graph
    4. Return competitive intelligence report

    Note: May take 30-120 seconds depending
    on number of competitors monitored.
    """

    request_id = str(uuid.uuid4())[:8]

    logger.info(
        f"[{request_id}] "
        f"Competitor scan started — "
        f"{len(request.competitors)} competitors"
    )

    competitors_data = [
        comp.model_dump()
        for comp in request.competitors
    ]

    initial_state = {
        "competitors": competitors_data,
        "report_date": request.report_date,
        "request_id": request_id,
        "error": None,
        "completed": False
    }

    try:
        result = await competitor_intelligence_graph.ainvoke(
            initial_state
        )

        logger.info(
            f"[{request_id}] "
            f"Competitor scan complete — "
            f"changes={result.get('total_changes_found')}"
        )

        return CompetitorResponse(
            request_id=request_id,
            report_date=result.get("report_date"),
            successful_scrapes=result.get(
                "successful_scrapes"
            ),
            failed_scrapes=result.get("failed_scrapes"),
            total_changes_found=result.get(
                "total_changes_found"
            ),
            competitor_analyses=result.get(
                "competitor_analyses"
            ),
            slack_report=result.get("slack_report"),
            report_summary=result.get("report_summary"),
            slack_channel=result.get("slack_channel"),
            report_ready=result.get("report_ready"),
            error=result.get("error"),
            completed=result.get("completed")
        )

    except Exception as e:
        logger.error(
            f"[{request_id}] "
            f"Competitor scan failed — {str(e)}"
        )
        raise HTTPException(
            status_code=500,
            detail=f"Agent failed: {str(e)}"
        )