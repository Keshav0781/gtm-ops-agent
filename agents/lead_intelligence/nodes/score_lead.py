"""
Node 3 — Score Lead

Third node in Lead Intelligence Agent.
Takes research results from state and
scores the lead as HIGH, MEDIUM, or LOW.

This is the qualification decision —
should our sales team spend time on this lead?

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
    Same dual LLM routing as research node.
    Groq by default, Ollama for GDPR compliance.
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
        temperature=0.1
    )


# Scoring prompt
# Defines our Ideal Customer Profile (ICP)
# ICP = description of perfect customer
# Every B2B company has one
SCORING_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are a B2B sales qualification expert.
        
        Score leads based on this Ideal Customer Profile (ICP):
        - Company size: 50-5000 employees (sweet spot)
        - Industries: Technology, Healthcare, Manufacturing,
          Finance, Automotive, Logistics
        - Has budget for software tools
        - Shows genuine interest in data/analytics
        
        Score rules:
        HIGH — Matches ICP well, clear business need,
               good company size, relevant industry
        MEDIUM — Partially matches ICP, some potential,
                 worth a follow up
        LOW — Does not match ICP, too small, wrong industry,
              or no clear need
        
        Always respond in this exact format:
        SCORE: [HIGH/MEDIUM/LOW]
        REASONING: [2-3 sentences explaining the score]
        IS_QUALIFIED: [true/false]"""
    ),
    (
        "human",
        """Score this lead:
        
        Company: {company_name}
        Industry: {industry}
        Size: {company_size}
        Their Message: {message}
        Research Summary: {research_summary}
        
        Provide score following exact format."""
    )
])


def parse_score_response(response_text: str) -> dict:
    """
    Parses LLM scoring response into structured fields.
    Same parsing pattern as research node.
    """
    result = {
        "score": "MEDIUM",
        "score_reasoning": response_text,
        "is_qualified": False
    }

    lines = response_text.strip().split("\n")

    for line in lines:
        if line.startswith("SCORE:"):
            score = line.replace("SCORE:", "").strip().upper()
            if score in ["HIGH", "MEDIUM", "LOW"]:
                result["score"] = score

        elif line.startswith("REASONING:"):
            result["score_reasoning"] = line.replace(
                "REASONING:", ""
            ).strip()

        elif line.startswith("IS_QUALIFIED:"):
            qualified = line.replace(
                "IS_QUALIFIED:", ""
            ).strip().lower()
            result["is_qualified"] = qualified == "true"

    return result


async def score_lead(state: LeadState) -> LeadState:
    """
    Node 3 — Score lead based on research.

    What it does:
    1. Checks if previous nodes failed
    2. Sends research data to LLM for scoring
    3. Parses score — HIGH, MEDIUM, LOW
    4. Updates state with score and reasoning

    Input state fields used:
        company_name, industry, company_size,
        message, research_summary

    Output state fields added:
        score, score_reasoning, is_qualified
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

    logger.info(
        f"[{state.get('request_id')}] "
        f"Node 3: Scoring lead for "
        f"{state['company_name']}"
    )

    # ==========================================
    # Step 2 — Call LLM for scoring
    # ==========================================
    try:
        llm = get_llm()
        chain = SCORING_PROMPT | llm

        response = await chain.ainvoke({
            "company_name": state["company_name"],
            "industry": state.get("industry", "Unknown"),
            "company_size": state.get(
                "company_size", "Unknown"
            ),
            "message": state.get(
                "message", "No message provided"
            ),
            "research_summary": state.get(
                "research_summary",
                "No research available"
            )
        })

        # ==========================================
        # Step 3 — Parse scoring response
        # ==========================================
        score_data = parse_score_response(response.content)

        # ==========================================
        # Step 4 — Update state with score
        # ==========================================
        state["score"] = score_data["score"]
        state["score_reasoning"] = score_data[
            "score_reasoning"
        ]
        state["is_qualified"] = score_data["is_qualified"]

        logger.info(
            f"[{state.get('request_id')}] "
            f"Node 3: Score complete — "
            f"score={state['score']} "
            f"qualified={state['is_qualified']}"
        )

    except Exception as e:
        logger.error(
            f"[{state.get('request_id')}] "
            f"Node 3: Scoring failed — {str(e)}"
        )
        # Default to MEDIUM on failure
        # Better than losing the lead entirely
        state["score"] = "MEDIUM"
        state["score_reasoning"] = (
            "Scoring unavailable — manual review needed"
        )
        state["is_qualified"] = True

    return state