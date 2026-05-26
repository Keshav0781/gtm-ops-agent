"""
Node 3 — Analyze Changes

Third node in Competitor Intelligence Agent.
Uses LLM to analyze scraped content and
identify meaningful changes.

This is where LLM adds real value —
understanding WHAT changed and WHY it matters
from a business perspective.

Pure string comparison would catch any text change.
LLM understands business significance:
"Pricing increased 15%" matters more than
"Footer copyright year updated"
"""

import logging
import os
from typing import List
from langchain_groq import ChatGroq
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from agents.competitor_intelligence.state import (
    CompetitorState
)

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
        temperature=0.1
    )


ANALYZE_CHANGES_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are a competitive intelligence analyst
        for a B2B SaaS company.

        Analyze competitor website content and identify
        meaningful business changes.

        Focus on:
        - Pricing changes — increases, decreases, new tiers
        - New features or products announced
        - New blog posts or content about strategy
        - Significant job postings indicating growth areas
        - Any messaging changes suggesting pivot

        Ignore:
        - Minor wording tweaks
        - Design changes you cannot see from text
        - Copyright year updates
        - Generic boilerplate text

        Always respond in this exact format:
        CHANGES_DETECTED: [true/false]
        SIGNIFICANT_CHANGES: [bullet points or NONE]
        BUSINESS_IMPACT: [why this matters to us or NONE]
        RECOMMENDED_ACTION: [what sales team should do or NONE]"""
    ),
    (
        "human",
        """Analyze this competitor:

        Competitor: {competitor_name}
        URL: {competitor_url}

        Current Content:
        {current_content}

        Previous Content (last week):
        {previous_content}

        Identify meaningful business changes."""
    )
])


def parse_analysis_response(response_text: str) -> dict:
    """
    Parses LLM analysis response.
    Same parsing pattern as all other nodes.
    """
    result = {
        "changes_detected": False,
        "significant_changes": "None",
        "business_impact": "None",
        "recommended_action": "None"
    }

    lines = response_text.strip().split("\n")
    changes_lines = []
    reading_changes = False

    for line in lines:
        if line.startswith("CHANGES_DETECTED:"):
            value = line.replace(
                "CHANGES_DETECTED:", ""
            ).strip().lower()
            result["changes_detected"] = value == "true"
            reading_changes = False

        elif line.startswith("SIGNIFICANT_CHANGES:"):
            reading_changes = True
            content = line.replace(
                "SIGNIFICANT_CHANGES:", ""
            ).strip()
            if content and content != "NONE":
                changes_lines.append(content)

        elif line.startswith("BUSINESS_IMPACT:"):
            reading_changes = False
            result["business_impact"] = line.replace(
                "BUSINESS_IMPACT:", ""
            ).strip()

        elif line.startswith("RECOMMENDED_ACTION:"):
            reading_changes = False
            result["recommended_action"] = line.replace(
                "RECOMMENDED_ACTION:", ""
            ).strip()

        elif reading_changes and line.strip():
            changes_lines.append(line.strip())

    if changes_lines:
        result["significant_changes"] = "\n".join(
            changes_lines
        )

    return result


async def analyze_changes(
    state: CompetitorState
) -> CompetitorState:
    """
    Node 3 — Analyze competitor changes with LLM.

    What it does:
    1. Checks if previous nodes failed
    2. For each competitor — calls LLM to analyze
    3. Identifies significant business changes
    4. Counts total changes found
    5. Updates state with analyses

    Input state fields used:
        scraped_data

    Output state fields added:
        competitor_analyses, total_changes_found,
        significant_changes
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

    scraped_data = state.get("scraped_data", [])

    logger.info(
        f"[{state.get('request_id')}] "
        f"Node 3: Analyzing {len(scraped_data)} competitors"
    )

    competitor_analyses = []
    significant_changes = []
    total_changes = 0

    llm = get_llm()
    chain = ANALYZE_CHANGES_PROMPT | llm

    # ==========================================
    # Step 2 — Analyze each competitor
    # ==========================================
    for competitor in scraped_data:
        name = competitor.get("name", "Unknown")

        if competitor.get("fetch_error"):
            logger.warning(
                f"[{state.get('request_id')}] "
                f"Node 3: Skipping {name} — fetch failed"
            )
            competitor_analyses.append({
                "name": name,
                "url": competitor.get("url", ""),
                "changes_detected": False,
                "significant_changes": "Fetch failed",
                "business_impact": "Unknown",
                "recommended_action": "Check URL manually",
                "error": competitor.get("fetch_error")
            })
            continue

        try:
            current = competitor.get(
                "current_content", {}
            )
            previous = competitor.get(
                "previous_content", {}
            )

            current_text = "\n\n".join([
                f"[{page}]\n{content}"
                for page, content in current.items()
                if content
            ])

            previous_text = "\n\n".join([
                f"[{page}]\n{content}"
                for page, content in previous.items()
                if content
            ]) if previous else "No previous data available"

            response = await chain.ainvoke({
                "competitor_name": name,
                "competitor_url": competitor.get(
                    "url", ""
                ),
                "current_content": current_text or (
                    "No content retrieved"
                ),
                "previous_content": previous_text
            })

            analysis = parse_analysis_response(
                response.content
            )
            analysis["name"] = name
            analysis["url"] = competitor.get("url", "")

            competitor_analyses.append(analysis)

            if analysis["changes_detected"]:
                total_changes += 1
                significant_changes.append(analysis)
                logger.info(
                    f"[{state.get('request_id')}] "
                    f"Node 3: Changes detected for {name}"
                )

        except Exception as e:
            logger.error(
                f"[{state.get('request_id')}] "
                f"Node 3: Analysis failed for "
                f"{name} — {str(e)}"
            )
            competitor_analyses.append({
                "name": name,
                "url": competitor.get("url", ""),
                "changes_detected": False,
                "significant_changes": "Analysis failed",
                "business_impact": "Unknown",
                "recommended_action": "Manual review needed",
                "error": str(e)
            })

    # ==========================================
    # Step 3 — Update state
    # ==========================================
    state["competitor_analyses"] = competitor_analyses
    state["total_changes_found"] = total_changes
    state["significant_changes"] = significant_changes

    logger.info(
        f"[{state.get('request_id')}] "
        f"Node 3: Analysis complete — "
        f"{total_changes} competitors with changes"
    )

    return state