"""
Node 4 — Draft Email

Final node in Lead Intelligence Agent.
Drafts personalised outreach email based
on lead score and research findings.

Handles all three score levels differently:
- HIGH: Full personalised email with research
- MEDIUM: Warm email with qualifying question  
- LOW: Lightweight nurturing acknowledgment



IMPORTANT: This node only DRAFTS the email.
It never sends. Human must approve first.
Zero autonomous outbound — GDPR compliant.
"""

import logging
import os
from langchain_groq import ChatGroq
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from agents.lead_intelligence.state import LeadState

logger = logging.getLogger(__name__)


def get_llm():
    """
    Same dual LLM routing as previous nodes.
    """
    provider = os.getenv("DEFAULT_LLM_PROVIDER", "groq")
    if provider == "ollama":
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
        temperature=0.3  # Slightly higher for creativity
    )


# HIGH score prompt — full personalised email
HIGH_SCORE_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are an expert B2B sales writer.
        Write a highly personalised, professional
        first outreach email.
        
        Rules:
        - Reference specific company details from research
        - Clear value proposition in first paragraph
        - One specific call to action (book a call)
        - Professional but warm tone
        - Maximum 150 words
        - Never mention score or AI
        
        Respond in exact format:
        SUBJECT: [email subject line]
        BODY: [email body]"""
    ),
    (
        "human",
        """Write outreach email for this HIGH scored lead:
        
        Company: {company_name}
        Contact: {contact_name}
        Industry: {industry}
        Size: {company_size}
        Their Message: {message}
        Research: {research_summary}
        
        Make it feel handwritten, not automated."""
    )
])

# MEDIUM score prompt — qualifying question
MEDIUM_SCORE_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are an expert B2B sales writer.
        Write a warm, brief email that acknowledges
        their interest and asks one qualifying question
        to better understand their needs.
        
        Rules:
        - Warm and genuine tone
        - Ask exactly ONE qualifying question
        - Maximum 100 words
        - No hard sell
        
        Respond in exact format:
        SUBJECT: [email subject line]
        BODY: [email body]"""
    ),
    (
        "human",
        """Write qualifying email for MEDIUM scored lead:
        
        Company: {company_name}
        Contact: {contact_name}
        Industry: {industry}
        Their Message: {message}
        
        Keep it brief and genuine."""
    )
])

# LOW score prompt — nurturing acknowledgment
LOW_SCORE_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are an expert B2B sales writer.
        Write a brief, warm acknowledgment email
        that keeps the door open without wasting
        either party's time.
        
        Rules:
        - Genuinely warm tone
        - Acknowledge their message
        - Ask one open question about their needs
        - Maximum 75 words
        - No pressure, no hard sell
        
        Respond in exact format:
        SUBJECT: [email subject line]
        BODY: [email body]"""
    ),
    (
        "human",
        """Write nurturing email for LOW scored lead:
        
        Company: {company_name}
        Contact: {contact_name}
        Their Message: {message}
        
        Keep door open, no pressure."""
    )
])


def get_prompt_for_score(score: str) -> ChatPromptTemplate:
    """
    Returns correct prompt based on lead score.
    Clean way to select between three approaches.
    """
    prompts = {
        "HIGH": HIGH_SCORE_PROMPT,
        "MEDIUM": MEDIUM_SCORE_PROMPT,
        "LOW": LOW_SCORE_PROMPT
    }
    return prompts.get(score, MEDIUM_SCORE_PROMPT)


def parse_email_response(response_text: str) -> dict:
    """
    Parses LLM email response into subject and body.
    Same parsing pattern as previous nodes.
    """
    result = {
        "subject": "Following up on your inquiry",
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


async def draft_email(state: LeadState) -> LeadState:
    """
    Node 4 — Draft personalised email based on score.

    What it does:
    1. Checks if previous nodes failed
    2. Selects correct prompt based on score
    3. Generates personalised email draft
    4. Updates state with subject and body

    Input state fields used:
        company_name, contact_name, industry,
        company_size, message, research_summary,
        score

    Output state fields added:
        draft_email_subject, draft_email_body,
        email_tone, completed
    """

    # ==========================================
    # Step 1 — Check if previous nodes failed
    # ==========================================
    if state.get("error"):
        logger.warning(
            f"[{state.get('request_id')}] "
            f"Node 4: Skipping — previous node failed"
        )
        return state

    score = state.get("score", "MEDIUM")

    logger.info(
        f"[{state.get('request_id')}] "
        f"Node 4: Drafting email for "
        f"{state['company_name']} "
        f"(score={score})"
    )

    # ==========================================
    # Step 2 — Select prompt and draft email
    # ==========================================
    try:
        llm = get_llm()
        prompt = get_prompt_for_score(score)
        chain = prompt | llm

        response = await chain.ainvoke({
            "company_name": state["company_name"],
            "contact_name": state.get(
                "contact_name", "there"
            ),
            "industry": state.get("industry", "your industry"),
            "company_size": state.get(
                "company_size", "Unknown"
            ),
            "message": state.get(
                "message", "No message provided"
            ),
            "research_summary": state.get(
                "research_summary", "No research available"
            )
        })

        # ==========================================
        # Step 3 — Parse email response
        # ==========================================
        email_data = parse_email_response(response.content)

        # ==========================================
        # Step 4 — Update state
        # ==========================================
        state["draft_email_subject"] = email_data["subject"]
        state["draft_email_body"] = email_data["body"]
        state["email_tone"] = (
            "formal" if score == "HIGH" else "casual"
        )
        state["completed"] = True

        logger.info(
            f"[{state.get('request_id')}] "
            f"Node 4: Email drafted — "
            f"subject='{state['draft_email_subject']}'"
        )

    except Exception as e:
        logger.error(
            f"[{state.get('request_id')}] "
            f"Node 4: Email drafting failed — {str(e)}"
        )
        # Provide fallback email
        state["draft_email_subject"] = (
            f"Re: Your inquiry from "
            f"{state['company_name']}"
        )
        state["draft_email_body"] = (
            f"Hi {state.get('contact_name', 'there')},\n\n"
            f"Thank you for reaching out. "
            f"I'd love to learn more about your needs "
            f"at {state['company_name']}.\n\n"
            f"Could we schedule a brief call this week?\n\n"
            f"Best regards"
        )
        state["completed"] = True

    return state