"""
Node 3 — Generate Summary

Third node in Meeting Intelligence Agent.
Generates clean readable meeting summary
combining transcript, action items, and decisions.

This summary goes directly to Slack so it must be:
- Concise — people read it in 30 seconds
- Complete — captures everything important
- Actionable — clear next steps visible


Business value:
Team member who missed meeting gets complete
picture in 30 seconds instead of reading
full transcript or asking colleagues.
"""

import logging
import os
from langchain_groq import ChatGroq
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from agents.meeting_intelligence.state import MeetingState

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
        temperature=0.2
    )


GENERATE_SUMMARY_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are an expert at writing concise
        meeting summaries for busy professionals.

        Write a summary that can be read in 30 seconds.
        It goes directly to Slack so use Slack formatting.

        Always respond in this exact format:
        SUMMARY: [2-3 sentence overview of meeting]
        KEY_OUTCOMES: [3-5 bullet points of main outcomes]
        NEXT_MEETING: [suggested next meeting or NONE]"""
    ),
    (
        "human",
        """Generate summary for this meeting:

        Title: {meeting_title}
        Date: {meeting_date}
        Type: {meeting_type}
        Attendees: {attendees}
        Topics: {topics_discussed}
        Decisions: {decisions_made}
        Action Items Count: {action_items_count}
        Blockers: {blockers_identified}

        Transcript Summary:
        {cleaned_transcript}

        Write concise professional summary."""
    )
])


def parse_summary_response(response_text: str) -> dict:
    """
    Parses LLM summary response.
    Same parsing pattern as all other nodes.
    """
    result = {
        "summary": response_text,
        "key_outcomes": "See meeting notes",
        "next_meeting_suggested": "None"
    }

    lines = response_text.strip().split("\n")
    outcomes_lines = []
    reading_outcomes = False

    for line in lines:
        if line.startswith("SUMMARY:"):
            result["summary"] = line.replace(
                "SUMMARY:", ""
            ).strip()
            reading_outcomes = False

        elif line.startswith("KEY_OUTCOMES:"):
            reading_outcomes = True
            content = line.replace(
                "KEY_OUTCOMES:", ""
            ).strip()
            if content:
                outcomes_lines.append(content)

        elif line.startswith("NEXT_MEETING:"):
            reading_outcomes = False
            result["next_meeting_suggested"] = line.replace(
                "NEXT_MEETING:", ""
            ).strip()

        elif reading_outcomes:
            outcomes_lines.append(line)

    if outcomes_lines:
        result["key_outcomes"] = "\n".join(
            outcomes_lines
        ).strip()

    return result


async def generate_summary(
    state: MeetingState
) -> MeetingState:
    """
    Node 3 — Generate meeting summary.

    What it does:
    1. Checks if previous nodes failed
    2. Generates concise meeting summary
    3. Extracts key outcomes
    4. Suggests next meeting if relevant
    5. Updates state

    Input state fields used:
        meeting_title, meeting_date, meeting_type,
        attendees, topics_discussed, decisions_made,
        action_items_count, blockers_identified,
        cleaned_transcript

    Output state fields added:
        summary, key_outcomes, next_meeting_suggested
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
        f"Node 3: Generating summary for "
        f"{state.get('meeting_title', 'Untitled Meeting')}"
    )

    # ==========================================
    # Step 2 — Call LLM for summary generation
    # ==========================================
    try:
        llm = get_llm()
        chain = GENERATE_SUMMARY_PROMPT | llm

        response = await chain.ainvoke({
            "meeting_title": state.get(
                "meeting_title", "Untitled Meeting"
            ),
            "meeting_date": state.get(
                "meeting_date", "Unknown"
            ),
            "meeting_type": state.get(
                "meeting_type", "general"
            ),
            "attendees": state.get(
                "attendees", "Not specified"
            ),
            "topics_discussed": state.get(
                "topics_discussed", "Not identified"
            ),
            "decisions_made": state.get(
                "decisions_made", "None recorded"
            ),
            "action_items_count": state.get(
                "action_items_count", 0
            ),
            "blockers_identified": state.get(
                "blockers_identified", "None"
            ),
            "cleaned_transcript": state.get(
                "cleaned_transcript",
                state.get("transcript", "")
            )
        })

        # ==========================================
        # Step 3 — Parse summary response
        # ==========================================
        summary_data = parse_summary_response(
            response.content
        )

        # ==========================================
        # Step 4 — Update state
        # ==========================================
        state["summary"] = summary_data["summary"]
        state["key_outcomes"] = summary_data["key_outcomes"]
        state["next_meeting_suggested"] = summary_data[
            "next_meeting_suggested"
        ]

        logger.info(
            f"[{state.get('request_id')}] "
            f"Node 3: Summary generated successfully"
        )

    except Exception as e:
        logger.error(
            f"[{state.get('request_id')}] "
            f"Node 3: Summary generation failed — {str(e)}"
        )
        state["summary"] = (
            f"Summary unavailable for "
            f"{state.get('meeting_title', 'this meeting')}. "
            f"Please review transcript manually."
        )
        state["key_outcomes"] = "See meeting transcript"
        state["next_meeting_suggested"] = "None"

    return state