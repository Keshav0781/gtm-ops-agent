"""
Node 2 — Extract Context

Second node in Email Triage Agent.
Takes classified email and extracts
deeper context about sender and request.

Think of this as the experienced team member
who reads the email carefully and asks:
"Who exactly is this person? What do they
actually need? How urgent is this really?"


Business value:
Without context extraction — team member
receives email with no background.
With context extraction — team member receives
full briefing before they even open the email.
"""

import logging
import os
from langchain_groq import ChatGroq
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from agents.email_triage.state import EmailState

logger = logging.getLogger(__name__)


def get_llm():
    """
    Dual LLM routing — same pattern across all agents.
    Email content is sensitive personal data.
    Ollama option ensures GDPR compliance —
    sensitive email content never leaves network.
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
    logger.info("Using Groq — cloud LLM")
    return ChatGroq(
        api_key=os.getenv("GROQ_API_KEY"),
        model="llama-3.3-70b-versatile",
        temperature=0.1
    )


EXTRACT_CONTEXT_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are an expert at extracting key business 
        context from B2B emails.

        Extract the following information:

        SENDER_COMPANY: Company the sender works for
        SENDER_ROLE: Their job title or role if mentioned
        CORE_REQUEST: The main thing they are asking for
                      in one clear sentence
        KEY_DETAILS: Any specific details, deadlines,
                     numbers, or requirements mentioned
        REQUIRES_IMMEDIATE_ACTION: true if mentions
                     urgent deadline, emergency, or
                     time-sensitive language. false otherwise

        If information is not available write UNKNOWN.

        Always respond in this exact format:
        SENDER_COMPANY: [company name or UNKNOWN]
        SENDER_ROLE: [role or UNKNOWN]
        CORE_REQUEST: [one clear sentence]
        KEY_DETAILS: [specific details or UNKNOWN]
        REQUIRES_IMMEDIATE_ACTION: [true/false]"""
    ),
    (
        "human",
        """Extract context from this email:

        From: {sender_name} <{sender_email}>
        Classification: {classification}
        Priority: {priority}
        Subject: {subject}
        Body: {body}

        Extract all available context."""
    )
])


def parse_context_response(response_text: str) -> dict:
    """
    Parses LLM context extraction response.
    Same parsing pattern as all other nodes.
    """
    result = {
        "sender_company": "Unknown",
        "sender_role": "Unknown",
        "core_request": "See original email",
        "key_details": "None identified",
        "requires_immediate_action": False
    }

    lines = response_text.strip().split("\n")

    for line in lines:
        if line.startswith("SENDER_COMPANY:"):
            result["sender_company"] = line.replace(
                "SENDER_COMPANY:", ""
            ).strip()

        elif line.startswith("SENDER_ROLE:"):
            result["sender_role"] = line.replace(
                "SENDER_ROLE:", ""
            ).strip()

        elif line.startswith("CORE_REQUEST:"):
            result["core_request"] = line.replace(
                "CORE_REQUEST:", ""
            ).strip()

        elif line.startswith("KEY_DETAILS:"):
            result["key_details"] = line.replace(
                "KEY_DETAILS:", ""
            ).strip()

        elif line.startswith("REQUIRES_IMMEDIATE_ACTION:"):
            value = line.replace(
                "REQUIRES_IMMEDIATE_ACTION:", ""
            ).strip().lower()
            result["requires_immediate_action"] = (
                value == "true"
            )

    return result


async def extract_context(state: EmailState) -> EmailState:
    """
    Node 2 — Extract deeper context from email.

    What it does:
    1. Checks if Node 1 failed — stops if so
    2. Skips if email is SPAM — no context needed
    3. Extracts sender company, role, core request
    4. Identifies if immediate action required
    5. Updates state with context

    Input state fields used:
        sender_name, sender_email, subject,
        body, classification, priority

    Output state fields added:
        sender_company, sender_role,
        core_request, key_details,
        requires_immediate_action
    """

    # ==========================================
    # Step 1 — Check if previous node failed
    # ==========================================
    if state.get("error"):
        logger.warning(
            f"[{state.get('request_id')}] "
            f"Node 2: Skipping — previous node failed"
        )
        return state

    # ==========================================
    # Step 2 — Skip context for SPAM
    # No point extracting context from spam
    # Saves unnecessary LLM call
    # ==========================================
    if state.get("classification") == "SPAM":
        logger.info(
            f"[{state.get('request_id')}] "
            f"Node 2: Skipping context extraction "
            f"for SPAM email"
        )
        state["core_request"] = "SPAM — no action needed"
        state["requires_immediate_action"] = False
        return state

    logger.info(
        f"[{state.get('request_id')}] "
        f"Node 2: Extracting context from "
        f"{state.get('classification')} email"
    )

    # ==========================================
    # Step 3 — Call LLM for context extraction
    # ==========================================
    try:
        llm = get_llm()
        chain = EXTRACT_CONTEXT_PROMPT | llm

        response = await chain.ainvoke({
            "sender_name": state.get(
                "sender_name", "Unknown"
            ),
            "sender_email": state.get(
                "sender_email", "unknown"
            ),
            "classification": state.get(
                "classification", "SUPPORT"
            ),
            "priority": state.get("priority", "MEDIUM"),
            "subject": state.get("subject", "No subject"),
            "body": state.get("body", "No body")
        })

        # ==========================================
        # Step 4 — Parse context response
        # ==========================================
        context_data = parse_context_response(
            response.content
        )

        # ==========================================
        # Step 5 — Update state with context
        # ==========================================
        state["sender_company"] = context_data[
            "sender_company"
        ]
        state["sender_role"] = context_data["sender_role"]
        state["core_request"] = context_data["core_request"]
        state["key_details"] = context_data["key_details"]
        state["requires_immediate_action"] = context_data[
            "requires_immediate_action"
        ]

        logger.info(
            f"[{state.get('request_id')}] "
            f"Node 2: Context extracted — "
            f"company={state['sender_company']} "
            f"urgent={state['requires_immediate_action']}"
        )

    except Exception as e:
        logger.error(
            f"[{state.get('request_id')}] "
            f"Node 2: Context extraction failed — {str(e)}"
        )
        state["sender_company"] = "Unknown"
        state["core_request"] = "See original email"
        state["requires_immediate_action"] = False

    return state