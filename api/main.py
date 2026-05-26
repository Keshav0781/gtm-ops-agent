"""
GTM Ops Agent - Main Application Entry Point
"""

import logging

from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from api.middleware.logging import RequestLoggingMiddleware
from api.routers import leads, emails, meetings, crm, competitors

# Load environment variables first — before anything else
load_dotenv()

# Configure logging — same pattern used at Siemens
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Runs on startup and shutdown.
    At Siemens this is where they initialise
    database connections, load models etc.
    """
    logger.info("GTM Ops Agent starting up...")
    logger.info("Environment loaded successfully")
    yield
    logger.info("GTM Ops Agent shutting down...")


# Create FastAPI app with full metadata
# This metadata appears in auto-generated API docs
app = FastAPI(
    title="GTM Ops Agent",
    description="""
    Production-grade GTM operations automation using 
    LangGraph multi-agent system, n8n workflow orchestration,
    and MCP tool integration.
    
    Agents:
    - Lead Intelligence: Research and score incoming leads
    - Email Triage: Classify and route incoming emails  
    - Meeting Intelligence: Summarise meetings and create tasks
    - CRM Hygiene: Detect and flag stale deals
    - Competitor Intelligence: Monitor competitor activity
    """,
    version="1.0.0",
    lifespan=lifespan
)

# CORS Middleware
# Allows dashboard and n8n to call our API
# At Siemens this is configured per environment
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Professional request logging middleware
# Adds unique request ID to every request
# At Siemens this enables end-to-end tracing
app.add_middleware(RequestLoggingMiddleware)

# ==========================================
# Register routers
# Each agent gets its own router
# At Siemens each service has dedicated routers
# ==========================================
app.include_router(leads.router)
app.include_router(emails.router)
app.include_router(meetings.router)
app.include_router(crm.router)
app.include_router(competitors.router)


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint — confirms API is running."""
    return {
        "service": "GTM Ops Agent",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint.
    Called every 30 seconds by Railway/Azure
    to verify service is alive.
    Returns 200 if healthy.
    """
    return {
        "status": "healthy",
        "service": "gtm-ops-agent",
        "version": "1.0.0"
    }