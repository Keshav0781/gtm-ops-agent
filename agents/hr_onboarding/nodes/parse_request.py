"""
Parse Request Node

First node in HR Onboarding Agent.

What it does:
- Receives raw natural language from HR
- Uses LLM to extract structured data
- Fills employee details in state

GDPR Note:
Uses dual LLM routing — same pattern as all agents.
Groq by default. Set DEFAULT_LLM_PROVIDER=ollama
in .env for full GDPR compliance.
Employee data stays on machine when using Ollama.
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
    HR data is sensitive — Ollama ensures data
    never leaves the machine.
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


def parse_request(
    state: HROnboardingState
) -> HROnboardingState:
    """
    Parse natural language HR request into
    structured employee data.
    """

    request_id = state.get("request_id", "unknown")
    onboarding_request = state.get(
        "onboarding_request", ""
    )

    logger.info(
        f"[{request_id}] "
        f"Parsing HR request: "
        f"{onboarding_request[:50]}..."
    )

    # ==========================================
    # Initialize LLM via dual routing
    # ==========================================
    llm = get_llm()

    # ==========================================
    # Prompt — extract structured data
    # Temperature 0 = consistent extraction
    # ==========================================
    prompt = f"""You are an HR system that extracts structured data from natural language onboarding requests.

Extract the following from the request:
- employee_name: full name of the new employee
- employee_email: email address if mentioned
- role: job title/role
- department: department based on role (Engineering/Product/Sales/Marketing/Operations)
- start_date: when they start
- manager_name: manager name if mentioned
- office_location: office location if mentioned

HR Request: {onboarding_request}

Respond ONLY with a JSON object. No other text. No backticks.
Example:
{{
    "employee_name": "Sarah Chen",
    "employee_email": "sarah@datasync.de",
    "role": "Product Designer",
    "department": "Product",
    "start_date": "Monday June 2nd",
    "manager_name": "Thomas Müller",
    "office_location": "Berlin"
}}

If any field is not mentioned use null."""

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
            f"Parsed successfully: "
            f"name={parsed.get('employee_name')} "
            f"role={parsed.get('role')}"
        )

        return {
            **state,
            "employee_name": parsed.get("employee_name"),
            "employee_email": parsed.get("employee_email"),
            "role": parsed.get("role"),
            "department": parsed.get("department"),
            "start_date": parsed.get("start_date"),
            "manager_name": parsed.get("manager_name"),
            "office_location": parsed.get("office_location"),
        }

    except Exception as e:
        logger.error(
            f"[{request_id}] "
            f"Parse failed: {str(e)}"
        )
        return {
            **state,
            "error": f"Parse failed: {str(e)}",
            "completed": False
        }