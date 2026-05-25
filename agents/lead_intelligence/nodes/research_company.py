"""
Node 2 — Research Company

Second node in Lead Intelligence Agent.
Takes company name from state and researches
it using Groq LLM.

Produces:
- Company size
- Industry
- Description
- Research summary

At Siemens this type of node uses Azure OpenAI
with internal knowledge bases. We use Groq
with web search — same concept, different provider.
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
    Returns correct LLM based on environment config.
    
    This is our dual LLM routing:
    - Groq: fast cloud inference (default)
    - Ollama: local, GDPR compliant
    
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
        temperature=0.1  # Low temperature = consistent outputs
    )


# Research prompt template
# Structured so LLM returns consistent format
# Easy to parse into state fields
RESEARCH_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are a B2B sales researcher. 
        Research the given company and provide structured information.
        
        Always respond in this exact format:
        COMPANY_SIZE: [number of employees or estimate]
        INDUSTRY: [primary industry]
        DESCRIPTION: [2-3 sentence company description]
        GROWTH_STAGE: [startup/growing/established/enterprise]
        SUMMARY: [3-4 sentences about why they might need 
                  a B2B analytics tool]
        
        If you cannot find information, write UNKNOWN for that field.
        Never make up specific numbers — use estimates if needed."""
    ),
    (
        "human",
        """Research this company for B2B sales purposes:
        
        Company Name: {company_name}
        Additional Context: {message}
        
        Provide structured research following the exact format."""
    )
])


def parse_research_response(response_text: str) -> dict:
    """
    Parses LLM response into structured fields.
    
    Why we parse instead of using raw text:
    - Consistent data in database
    - Scoring node can use specific fields
    - Easy to display in dashboard
    
    """
    result = {
        "company_size": "Unknown",
        "industry": "Unknown",
        "company_description": "Unknown",
        "research_summary": response_text
    }

    lines = response_text.strip().split("\n")

    for line in lines:
        if line.startswith("COMPANY_SIZE:"):
            result["company_size"] = line.replace(
                "COMPANY_SIZE:", ""
            ).strip()
        elif line.startswith("INDUSTRY:"):
            result["industry"] = line.replace(
                "INDUSTRY:", ""
            ).strip()
        elif line.startswith("DESCRIPTION:"):
            result["company_description"] = line.replace(
                "DESCRIPTION:", ""
            ).strip()
        elif line.startswith("SUMMARY:"):
            result["research_summary"] = line.replace(
                "SUMMARY:", ""
            ).strip()

    return result


async def research_company(state: LeadState) -> LeadState:
    """
    Node 2 — Research company using LLM.

    What it does:
    1. Checks if parse_lead failed — stops if so
    2. Gets correct LLM (Groq or Ollama)
    3. Sends research prompt to LLM
    4. Parses structured response
    5. Updates state with research findings

    Input state fields used:
        company_name, message, request_id

    Output state fields added:
        company_size, industry,
        company_description, research_summary,
        research_completed
    """

    # ==========================================
    # Step 1 — Check if previous node failed
    # If parse_lead set an error — stop here
    # No point researching invalid data
    # ==========================================
    if state.get("error"):
        logger.warning(
            f"[{state.get('request_id')}] "
            f"Node 2: Skipping — previous node failed"
        )
        return state

    logger.info(
        f"[{state.get('request_id')}] "
        f"Node 2: Researching {state['company_name']}"
    )

    # ==========================================
    # Step 2 — Call LLM for research
    # ==========================================
    try:
        llm = get_llm()
        chain = RESEARCH_PROMPT | llm

        response = await chain.ainvoke({
            "company_name": state["company_name"],
            "message": state.get("message", "No message provided")
        })

        # ==========================================
        # Step 3 — Parse structured response
        # ==========================================
        research_data = parse_research_response(
            response.content
        )

        # ==========================================
        # Step 4 — Update state with findings
        # ==========================================
        state["company_size"] = research_data["company_size"]
        state["industry"] = research_data["industry"]
        state["company_description"] = research_data[
            "company_description"
        ]
        state["research_summary"] = research_data[
            "research_summary"
        ]
        state["research_completed"] = True

        logger.info(
            f"[{state.get('request_id')}] "
            f"Node 2: Research complete — "
            f"industry={state['industry']} "
            f"size={state['company_size']}"
        )

    except Exception as e:
        # Research failed — log but don't stop
        # We can still score with partial data
        logger.error(
            f"[{state.get('request_id')}] "
            f"Node 2: Research failed — {str(e)}"
        )
        state["research_completed"] = False
        state["research_summary"] = (
            f"Research unavailable for "
            f"{state['company_name']}"
        )

    return state