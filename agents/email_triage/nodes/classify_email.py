"""
Node 1 — Classify Email

First node in Email Triage Agent.
Receives raw email data and classifies
what type of email it is.

Think of this as the first human who
reads the email and decides:
"Is this sales, support, spam, or something else?"

Business value:
Without this node — someone spends 2-3 minutes
per email just figuring out what it is.
With this node — classified in under 1 second.
"""

import logging
import os
from langchain_groq import ChatGroq
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from agents.email_triage.state import EmailState

logger = logging.getLogger(__name__)


def get_llm():
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


CLASSIFY_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are an expert email classifier for a B2B
        software company.

        Classify emails into exactly one type that best
        describes the email. Common types include:

        SALES — potential customer interested in buying
        SUPPORT — existing customer needs help
        PARTNERSHIP — another company wants to collaborate
        PRESS — journalist or media inquiry
        FINANCE — invoice, payment, or billing related
        SPAM — irrelevant or unsolicited
        RECRUITING — job application or candidate inquiry
        INVESTOR — investment or funding inquiry

        If the email does not fit any of the above types,
        create a short descriptive uppercase label that
        best describes it. For example: LEGAL, VENDOR,
        COMPLAINT, FEEDBACK etc.

        Priority levels:
        HIGH — needs response within 2 hours
        MEDIUM — needs response within 24 hours
        LOW — needs response within 72 hours

        Sentiment:
        POSITIVE — excited, interested, happy
        NEUTRAL — informational, no strong emotion
        NEGATIVE — frustrated, angry, complaining
        URGENT — time-sensitive, emergency language

        Always respond in this exact format:
        CLASSIFICATION: [type]
        PRIORITY: [level]
        SENTIMENT: [sentiment]
        REASONING: [one sentence explanation]"""
    ),
    (
        "human",
        """Classify this email:

        From: {sender_email}
        Subject: {subject}
        Body: {body}

        Provide classification following exact format."""
    )
])


def parse_classification_response(response_text: str) -> dict:
    """
    Parses LLM classification response.
    No hardcoded valid list — LLM decides the category.
    Falls back to UNKNOWN only if response is empty.
    """
    result = {
        "classification": "UNKNOWN",
        "priority": "MEDIUM",
        "sentiment": "NEUTRAL",
        "classification_reasoning": response_text
    }

    lines = response_text.strip().split("\n")

    for line in lines:
        if line.startswith("CLASSIFICATION:"):
            value = line.replace(
                "CLASSIFICATION:", ""
            ).strip().upper()
            if value:
                result["classification"] = value

        elif line.startswith("PRIORITY:"):
            value = line.replace(
                "PRIORITY:", ""
            ).strip().upper()
            if value in ["HIGH", "MEDIUM", "LOW"]:
                result["priority"] = value

        elif line.startswith("SENTIMENT:"):
            value = line.replace(
                "SENTIMENT:", ""
            ).strip().upper()
            if value in [
                "POSITIVE", "NEUTRAL",
                "NEGATIVE", "URGENT"
            ]:
                result["sentiment"] = value

        elif line.startswith("REASONING:"):
            result["classification_reasoning"] = line.replace(
                "REASONING:", ""
            ).strip()

    return result


async def classify_email(state: EmailState) -> EmailState:
    if not state.get("body") and not state.get("subject"):
        logger.error(
            f"[{state.get('request_id')}] "
            f"Node 1: Cannot classify — "
            f"no subject or body provided"
        )
        state["error"] = "Email body or subject required"
        state["completed"] = False
        return state

    logger.info(
        f"[{state.get('request_id')}] "
        f"Node 1: Classifying email from "
        f"{state.get('sender_email', 'unknown')}"
    )

    try:
        llm = get_llm()
        chain = CLASSIFY_PROMPT | llm

        response = await chain.ainvoke({
            "sender_email": state.get(
                "sender_email", "unknown"
            ),
            "subject": state.get(
                "subject", "No subject"
            ),
            "body": state.get("body", "No body")
        })

        classification_data = parse_classification_response(
            response.content
        )

        state["classification"] = classification_data[
            "classification"
        ]
        state["priority"] = classification_data["priority"]
        state["sentiment"] = classification_data["sentiment"]
        state["classification_reasoning"] = (
            classification_data["classification_reasoning"]
        )

        logger.info(
            f"[{state.get('request_id')}] "
            f"Node 1: Classification complete — "
            f"type={state['classification']} "
            f"priority={state['priority']} "
            f"sentiment={state['sentiment']}"
        )

    except Exception as e:
        logger.error(
            f"[{state.get('request_id')}] "
            f"Node 1: Classification failed — {str(e)}"
        )
        state["classification"] = "SUPPORT"
        state["priority"] = "MEDIUM"
        state["sentiment"] = "NEUTRAL"
        state["classification_reasoning"] = (
            "Classification unavailable — manual review needed"
        )

    return state
