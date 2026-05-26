"""
Node 1 — Extract Transcript

First node in Meeting Intelligence Agent.
Receives raw meeting transcript or notes
and cleans/structures them for processing.

Real scenario:
Google Meet or Zoom generates a transcript.
It is messy — speaker labels, timestamps,
filler words, repeated sentences.
This node cleans it into structured content.



Business value:
Raw transcript is unusable for extraction.
Clean structured content enables accurate
action item and decision extraction in Node 2.
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
    Meeting transcripts contain sensitive business
    discussions — Ollama option keeps data on-premise.
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


EXTRACT_TRANSCRIPT_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are an expert meeting analyst.
        Analyse the meeting transcript or notes
        and extract structured information.

        Always respond in this exact format:
        MEETING_TYPE: [standup/planning/review/
                       client_call/interview/general]
        TOPICS_DISCUSSED: [comma separated list
                          of main topics covered]
        PARTICIPANTS_IDENTIFIED: [names mentioned
                                  in transcript]
        CLEANED_CONTENT: [clean version of transcript
                         removing timestamps, filler
                         words, and repetitions —
                         keep all important content]"""
    ),
    (
        "human",
        """Analyse this meeting:

        Title: {meeting_title}
        Date: {meeting_date}
        Attendees: {attendees}
        Duration: {duration_minutes} minutes

        Transcript/Notes:
        {transcript}

        Extract structured information."""
    )
])


def parse_transcript_response(response_text: str) -> dict:
    """
    Parses LLM transcript extraction response.
    Same parsing pattern as all other nodes.
    """
    result = {
        "meeting_type": "general",
        "topics_discussed": "Not identified",
        "participants_identified": "Not identified",
        "cleaned_transcript": response_text
    }

    lines = response_text.strip().split("\n")
    cleaned_lines = []
    reading_cleaned = False

    for line in lines:
        if line.startswith("MEETING_TYPE:"):
            value = line.replace(
                "MEETING_TYPE:", ""
            ).strip().lower()
            valid_types = [
                "standup", "planning", "review",
                "client_call", "interview", "general"
            ]
            if value in valid_types:
                result["meeting_type"] = value

        elif line.startswith("TOPICS_DISCUSSED:"):
            result["topics_discussed"] = line.replace(
                "TOPICS_DISCUSSED:", ""
            ).strip()

        elif line.startswith("PARTICIPANTS_IDENTIFIED:"):
            result["participants_identified"] = line.replace(
                "PARTICIPANTS_IDENTIFIED:", ""
            ).strip()

        elif line.startswith("CLEANED_CONTENT:"):
            reading_cleaned = True
            content = line.replace(
                "CLEANED_CONTENT:", ""
            ).strip()
            if content:
                cleaned_lines.append(content)

        elif reading_cleaned:
            cleaned_lines.append(line)

    if cleaned_lines:
        result["cleaned_transcript"] = "\n".join(
            cleaned_lines
        ).strip()

    return result


async def extract_transcript(
    state: MeetingState
) -> MeetingState:
    """
    Node 1 — Extract and clean meeting transcript.

    What it does:
    1. Validates transcript exists
    2. Identifies meeting type
    3. Extracts topics and participants
    4. Cleans transcript for downstream nodes

    Input state fields used:
        meeting_title, meeting_date,
        attendees, transcript, duration_minutes

    Output state fields added:
        meeting_type, topics_discussed,
        participants_identified, cleaned_transcript
    """

    # ==========================================
    # Step 1 — Validate transcript exists
    # Cannot process without content
    # ==========================================
    if not state.get("transcript"):
        logger.error(
            f"[{state.get('request_id')}] "
            f"Node 1: No transcript provided"
        )
        state["error"] = "Meeting transcript is required"
        state["completed"] = False
        return state

    logger.info(
        f"[{state.get('request_id')}] "
        f"Node 1: Extracting transcript for "
        f"{state.get('meeting_title', 'Untitled Meeting')}"
    )

    # ==========================================
    # Step 2 — Call LLM for extraction
    # ==========================================
    try:
        llm = get_llm()
        chain = EXTRACT_TRANSCRIPT_PROMPT | llm

        response = await chain.ainvoke({
            "meeting_title": state.get(
                "meeting_title", "Untitled Meeting"
            ),
            "meeting_date": state.get(
                "meeting_date", "Unknown date"
            ),
            "attendees": state.get(
                "attendees", "Not specified"
            ),
            "duration_minutes": state.get(
                "duration_minutes", 0
            ),
            "transcript": state["transcript"]
        })

        # ==========================================
        # Step 3 — Parse response
        # ==========================================
        transcript_data = parse_transcript_response(
            response.content
        )

        # ==========================================
        # Step 4 — Update state
        # ==========================================
        state["meeting_type"] = transcript_data[
            "meeting_type"
        ]
        state["topics_discussed"] = transcript_data[
            "topics_discussed"
        ]
        state["participants_identified"] = transcript_data[
            "participants_identified"
        ]
        state["cleaned_transcript"] = transcript_data[
            "cleaned_transcript"
        ]

        logger.info(
            f"[{state.get('request_id')}] "
            f"Node 1: Transcript extracted — "
            f"type={state['meeting_type']} "
            f"topics={state['topics_discussed']}"
        )

    except Exception as e:
        logger.error(
            f"[{state.get('request_id')}] "
            f"Node 1: Extraction failed — {str(e)}"
        )
        state["meeting_type"] = "general"
        state["cleaned_transcript"] = state["transcript"]
        state["topics_discussed"] = "Extraction unavailable"
        state["participants_identified"] = state.get(
            "attendees", "Unknown"
        )

    return state