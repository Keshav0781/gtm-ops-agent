"""
Node 3 — Draft Reply

Third node in Email Triage Agent.
Drafts appropriate reply to sender
based on email classification and context.

Different email types get different reply styles:
SALES — warm, enthusiastic, next step focused
SUPPORT — empathetic, solution focused, ETA given
PARTNERSHIP — professional, open, CEO involvement hinted
PRESS — brief, professional, PR awareness
FINANCE — formal, confirmation focused
SPAM — no reply drafted

CRITICAL: This node only DRAFTS.
Never sends. Human must approve first.
Same principle as Lead Intelligence Agent.
Zero autonomous outbound — GDPR compliant.
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
        temperature=0.3
    )


# SALES reply — warm and next step focused
SALES_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are an expert B2B sales writer.
        Write a warm professional acknowledgment
        that moves the conversation forward.

        Rules:
        - Acknowledge their specific interest
        - Show genuine enthusiasm
        - Propose clear next step — book a call
        - Maximum 100 words
        - Never mention AI or automation

        Respond in exact format:
        SUBJECT: [reply subject]
        BODY: [reply body]"""
    ),
    (
        "human",
        """Write sales reply for this email:

        From: {sender_name} at {sender_company}
        Their request: {core_request}
        Key details: {key_details}
        Original subject: {subject}

        Make it warm and move conversation forward."""
    )
])

# SUPPORT reply — empathetic and solution focused
SUPPORT_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are an expert customer support writer.
        Write an empathetic acknowledgment that
        reassures the customer help is coming.

        Rules:
        - Acknowledge their frustration if negative
        - Confirm you received their request
        - Give realistic response time expectation
        - Maximum 80 words
        - Warm and human tone

        Respond in exact format:
        SUBJECT: [reply subject]
        BODY: [reply body]"""
    ),
    (
        "human",
        """Write support reply for this email:

        From: {sender_name} at {sender_company}
        Their issue: {core_request}
        Sentiment: {sentiment}
        Urgent: {requires_immediate_action}
        Original subject: {subject}

        Be empathetic and reassuring."""
    )
])

# PARTNERSHIP reply — professional and open
PARTNERSHIP_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are writing on behalf of a B2B company CEO.
        Write a professional acknowledgment that
        shows genuine interest without committing.

        Rules:
        - Professional and warm tone
        - Show genuine interest
        - Suggest introductory call
        - Maximum 80 words

        Respond in exact format:
        SUBJECT: [reply subject]
        BODY: [reply body]"""
    ),
    (
        "human",
        """Write partnership reply for this email:

        From: {sender_name} at {sender_company}
        Their proposal: {core_request}
        Original subject: {subject}

        Professional and genuinely interested."""
    )
])

# FINANCE reply — formal confirmation
FINANCE_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        """Write a brief formal acknowledgment
        confirming receipt of finance communication.

        Rules:
        - Formal tone
        - Confirm receipt
        - State who will follow up
        - Maximum 50 words

        Respond in exact format:
        SUBJECT: [reply subject]
        BODY: [reply body]"""
    ),
    (
        "human",
        """Write finance acknowledgment for:

        From: {sender_name} at {sender_company}
        Matter: {core_request}
        Original subject: {subject}"""
    )
])

# PRESS reply — brief and PR aware
PRESS_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        """Write a brief professional acknowledgment
        for a press or media inquiry.

        Rules:
        - Professional and brief
        - Acknowledge their inquiry
        - Say press team will follow up
        - Maximum 50 words
        - Never make any statements about company

        Respond in exact format:
        SUBJECT: [reply subject]
        BODY: [reply body]"""
    ),
    (
        "human",
        """Write press acknowledgment for:

        From: {sender_name}
        Their inquiry: {core_request}
        Original subject: {subject}"""
    )
])


def get_prompt_for_classification(
    classification: str
) -> ChatPromptTemplate:
    """
    Returns correct prompt based on email classification.
    Same pattern as draft_email node in Lead Intelligence.
    """
    prompts = {
        "SALES": SALES_PROMPT,
        "SUPPORT": SUPPORT_PROMPT,
        "PARTNERSHIP": PARTNERSHIP_PROMPT,
        "FINANCE": FINANCE_PROMPT,
        "PRESS": PRESS_PROMPT
    }
    return prompts.get(classification, SUPPORT_PROMPT)


def parse_reply_response(response_text: str) -> dict:
    """
    Parses LLM reply response into subject and body.
    Same parsing pattern as all other nodes.
    """
    result = {
        "subject": "Re: Your message",
        "body": response_text
    }

    lines = response_text.strip().split("\n")
    body_lines = []
    reading_body = False

    for line in lines:
        if line.startswith("SUBJECT:"):
            result["subject"] = line.replace(
                "SUBJECT:", ""
            ).strip()
        elif line.startswith("BODY:"):
            reading_body = True
            body_content = line.replace("BODY:", "").strip()
            if body_content:
                body_lines.append(body_content)
        elif reading_body:
            body_lines.append(line)

    if body_lines:
        result["body"] = "\n".join(body_lines).strip()

    return result


async def draft_reply(state: EmailState) -> EmailState:
    """
    Node 3 — Draft appropriate reply to sender.

    What it does:
    1. Checks if previous nodes failed
    2. Skips SPAM — no reply needed
    3. Selects correct prompt based on classification
    4. Generates personalised reply
    5. Updates state with draft reply

    Input state fields used:
        classification, sender_name, sender_company,
        core_request, key_details, sentiment,
        requires_immediate_action, subject

    Output state fields added:
        draft_reply_subject, draft_reply_body,
        reply_tone
    """

    # ==========================================
    # Step 1 — Check if previous nodes failed
    # ==========================================
    if state.get("error"):
        logger.warning(
            f"[{state.get('request_id')}] "
            f"Node 3: Skipping — previous node failed"
        )
        return state

    # ==========================================
    # Step 2 — Skip SPAM — no reply needed
    # ==========================================
    if state.get("classification") == "SPAM":
        logger.info(
            f"[{state.get('request_id')}] "
            f"Node 3: Skipping reply for SPAM email"
        )
        return state

    classification = state.get("classification", "SUPPORT")

    logger.info(
        f"[{state.get('request_id')}] "
        f"Node 3: Drafting {classification} reply"
    )

    # ==========================================
    # Step 3 — Select prompt and draft reply
    # ==========================================
    try:
        llm = get_llm()
        prompt = get_prompt_for_classification(classification)
        chain = prompt | llm

        response = await chain.ainvoke({
            "sender_name": state.get(
                "sender_name", "there"
            ),
            "sender_company": state.get(
                "sender_company", "your company"
            ),
            "core_request": state.get(
                "core_request", "your inquiry"
            ),
            "key_details": state.get(
                "key_details", "none"
            ),
            "sentiment": state.get("sentiment", "NEUTRAL"),
            "requires_immediate_action": state.get(
                "requires_immediate_action", False
            ),
            "subject": state.get("subject", "your message")
        })

        # ==========================================
        # Step 4 — Parse reply response
        # ==========================================
        reply_data = parse_reply_response(response.content)

        # ==========================================
        # Step 5 — Update state
        # ==========================================
        state["draft_reply_subject"] = reply_data["subject"]
        state["draft_reply_body"] = reply_data["body"]
        state["reply_tone"] = (
            "formal" if classification in [
                "FINANCE", "PRESS"
            ] else "friendly"
        )

        logger.info(
            f"[{state.get('request_id')}] "
            f"Node 3: Reply drafted — "
            f"subject='{state['draft_reply_subject']}'"
        )

    except Exception as e:
        logger.error(
            f"[{state.get('request_id')}] "
            f"Node 3: Reply drafting failed — {str(e)}"
        )
        state["draft_reply_subject"] = (
            f"Re: {state.get('subject', 'Your message')}"
        )
        state["draft_reply_body"] = (
            f"Hi {state.get('sender_name', 'there')},\n\n"
            f"Thank you for reaching out. "
            f"A member of our team will be in touch shortly."
            f"\n\nBest regards"
        )
        state["reply_tone"] = "friendly"

    return state