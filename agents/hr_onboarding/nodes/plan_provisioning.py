"""
Plan Provisioning Node

Second node in HR Onboarding Agent.

What it does:
- Receives structured employee data from parse_request
- Uses LLM to decide what systems to provision
- Decision based on role and department
- No actions taken yet — planning only

Role to systems mapping:
- Product Designer → Drive, Calendar, Slack, Gmail, Figma
- AI Engineer → Drive, Calendar, Slack, Gmail, GitHub
- Sales Executive → Drive, Calendar, Slack, Gmail, HubSpot
- Marketing Manager → Drive, Calendar, Slack, Gmail, Notion
- HR Manager → Drive, Calendar, Slack, Gmail, Notion

GDPR Note:
Uses dual LLM routing — same pattern as all agents.
"""

import json
import logging
import os
from langchain_groq import ChatGroq
from langchain_ollama import ChatOllama
from ..state import HROnboardingState

logger = logging.getLogger(__name__)


def get_llm():
    """
    Dual LLM routing — same pattern as all agents.
    Groq by default, Ollama for GDPR compliance.
    """
    provider = os.getenv("DEFAULT_LLM_PROVIDER", "groq")
    if provider == "ollama":
        logger.info("Using Ollama — local GDPR compliant LLM")
        return ChatOllama(
            base_url=os.getenv(
                "OLLAMA_BASE_URL",
                "http://localhost:11434"
            ),
            model=os.getenv("OLLAMA_MODEL", "llama3.2")
        )
    return ChatGroq(
        api_key=os.getenv("GROQ_API_KEY"),
        model="llama-3.3-70b-versatile",
        temperature=0
    )


def plan_provisioning(
    state: HROnboardingState
) -> HROnboardingState:
    """
    Decide what systems to provision based on role.
    No actual provisioning happens here — planning only.
    """

    request_id = state.get("request_id", "unknown")
    employee_name = state.get("employee_name", "")
    role = state.get("role", "")
    department = state.get("department", "")

    logger.info(
        f"[{request_id}] "
        f"Planning provisioning for "
        f"{employee_name} — {role}"
    )

    # ==========================================
    # Check for parse errors
    # ==========================================
    if state.get("error"):
        return state

    # ==========================================
    # Initialize LLM via dual routing
    # ==========================================
    llm = get_llm()

    # ==========================================
    # Prompt — decide provisioning plan
    # ==========================================
    prompt = f"""You are an IT provisioning system for DataSync GmbH, a B2B SaaS startup.

New employee details:
- Name: {employee_name}
- Role: {role}
- Department: {department}

Available systems:
- Google Drive (everyone needs this)
- Google Calendar (everyone needs this)
- Slack (everyone needs this)
- Gmail welcome email (everyone needs this)
- GitHub (Engineers only)
- Figma (Designers only)
- Notion (Product, Marketing, Operations)
- HubSpot (Sales only)

Slack channels at DataSync GmbH:
- #general (everyone)
- #engineering (engineers only)
- #design (designers only)
- #product (product team)
- #sales (sales team)
- #marketing (marketing team)

Based on the role decide the provisioning plan.

Respond ONLY with a JSON object. No other text. No backticks.
{{
    "systems_to_provision": ["Google Drive", "Google Calendar", "Slack", "Gmail"],
    "slack_channels": ["#general", "#design", "#product"],
    "drive_folder_name": "{employee_name}",
    "drive_folder_path": "/Team/{department}/{employee_name}",
    "requires_github": false,
    "requires_figma": true,
    "manual_systems": ["Figma"],
    "provisioning_plan_summary": "Will provision Google Drive, Calendar, Slack and Gmail for {employee_name}. Figma requires manual admin invite."
}}"""

    # ==========================================
    # Call LLM
    # ==========================================
    try:
        response = llm.invoke(prompt)

        # Handle both ChatGroq and ChatOllama
        if hasattr(response, "content"):
            raw_text = response.content.strip()
        else:
            raw_text = str(response).strip()

        # Clean JSON if wrapped in backticks
        if "```" in raw_text:
            raw_text = raw_text.split("```")[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:]

        # Find JSON object in response
        start = raw_text.find("{")
        end = raw_text.rfind("}") + 1
        if start != -1 and end > start:
            raw_text = raw_text[start:end]

        parsed = json.loads(raw_text)

        logger.info(
            f"[{request_id}] "
            f"Provisioning plan ready: "
            f"systems={parsed.get('systems_to_provision')}"
        )

        return {
            **state,
            "systems_to_provision": parsed.get(
                "systems_to_provision", []
            ),
            "slack_channels": parsed.get(
                "slack_channels", ["#general"]
            ),
            "drive_folder_name": parsed.get(
                "drive_folder_name", employee_name
            ),
            "drive_folder_path": parsed.get(
                "drive_folder_path",
                f"/Team/{department}/{employee_name}"
            ),
            "requires_github": parsed.get(
                "requires_github", False
            ),
            "requires_figma": parsed.get(
                "requires_figma", False
            ),
            "provisioning_plan_summary": parsed.get(
                "provisioning_plan_summary", ""
            ),
        }

    except Exception as e:
        logger.error(
            f"[{request_id}] "
            f"Planning failed: {str(e)}"
        )
        return {
            **state,
            "error": f"Planning failed: {str(e)}",
            "completed": False
        }