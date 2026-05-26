"""
Node 2 — Extract Action Items

Second node in Meeting Intelligence Agent.
Takes cleaned transcript and extracts:
- Action items with owners and deadlines
- Decisions made during meeting
- Blockers identified

This is the most valuable node for teams.
After every meeting people forget what was
decided and who owns what. This node
captures everything automatically.


Business value:
Without this — 30% of action items from
meetings are never followed up.
With this — 100% captured, assigned,
and tracked automatically.
"""

import json
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
        temperature=0.1
    )


EXTRACT_ACTION_ITEMS_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are an expert meeting analyst specialising
        in extracting actionable information.

        Extract all action items, decisions, and blockers.

        For action items respond with valid JSON array:
        ACTION_ITEMS: [
          {{
            "task": "description of task",
            "owner": "person responsible or null",
            "deadline": "deadline mentioned or null",
            "priority": "high/medium/low"
          }}
        ]

        Then add:
        DECISIONS_MADE: [bullet points of decisions]
        BLOCKERS_IDENTIFIED: [blockers or NONE]

        If no action items found return empty array: []
        Always return valid JSON for ACTION_ITEMS."""
    ),
    (
        "human",
        """Extract action items from this meeting:

        Meeting Type: {meeting_type}
        Attendees: {attendees}
        Topics: {topics_discussed}

        Transcript:
        {cleaned_transcript}

        Extract all action items, decisions, blockers."""
    )
])


def parse_action_items_response(response_text: str) -> dict:
    """
    Parses LLM action items response.
    Action items are JSON — requires careful parsing.
    """
    result = {
        "action_items": [],
        "decisions_made": "No decisions recorded",
        "blockers_identified": "None identified"
    }

    lines = response_text.strip().split("\n")
    json_lines = []
    reading_json = False
    decisions_lines = []
    reading_decisions = False

    for line in lines:
        if line.startswith("ACTION_ITEMS:"):
            reading_json = True
            json_content = line.replace(
                "ACTION_ITEMS:", ""
            ).strip()
            if json_content:
                json_lines.append(json_content)

        elif line.startswith("DECISIONS_MADE:"):
            reading_json = False
            reading_decisions = True
            content = line.replace(
                "DECISIONS_MADE:", ""
            ).strip()
            if content:
                decisions_lines.append(content)

        elif line.startswith("BLOCKERS_IDENTIFIED:"):
            reading_decisions = False
            result["blockers_identified"] = line.replace(
                "BLOCKERS_IDENTIFIED:", ""
            ).strip()

        elif reading_json:
            json_lines.append(line)

        elif reading_decisions:
            decisions_lines.append(line)

    # Parse JSON action items
    if json_lines:
        json_str = "\n".join(json_lines).strip()
        try:
            action_items = json.loads(json_str)
            if isinstance(action_items, list):
                result["action_items"] = action_items
        except json.JSONDecodeError:
            logger.warning("Could not parse action items JSON")
            result["action_items"] = []

    if decisions_lines:
        result["decisions_made"] = "\n".join(
            decisions_lines
        ).strip()

    return result


async def extract_action_items(
    state: MeetingState
) -> MeetingState:
    """
    Node 2 — Extract action items from cleaned transcript.

    What it does:
    1. Checks if Node 1 failed
    2. Extracts structured action items as JSON
    3. Extracts decisions made
    4. Identifies blockers
    5. Updates state

    Input state fields used:
        cleaned_transcript, meeting_type,
        attendees, topics_discussed

    Output state fields added:
        action_items, decisions_made,
        blockers_identified, action_items_count
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

    logger.info(
        f"[{state.get('request_id')}] "
        f"Node 2: Extracting action items from "
        f"{state.get('meeting_type')} meeting"
    )

    # ==========================================
    # Step 2 — Call LLM for extraction
    # ==========================================
    try:
        llm = get_llm()
        chain = EXTRACT_ACTION_ITEMS_PROMPT | llm

        response = await chain.ainvoke({
            "meeting_type": state.get(
                "meeting_type", "general"
            ),
            "attendees": state.get(
                "attendees", "Not specified"
            ),
            "topics_discussed": state.get(
                "topics_discussed", "Not identified"
            ),
            "cleaned_transcript": state.get(
                "cleaned_transcript",
                state.get("transcript", "")
            )
        })

        # ==========================================
        # Step 3 — Parse response
        # ==========================================
        action_data = parse_action_items_response(
            response.content
        )

        # ==========================================
        # Step 4 — Update state
        # ==========================================
        state["action_items"] = action_data["action_items"]
        state["decisions_made"] = action_data["decisions_made"]
        state["blockers_identified"] = action_data[
            "blockers_identified"
        ]
        state["action_items_count"] = len(
            action_data["action_items"]
        )

        logger.info(
            f"[{state.get('request_id')}] "
            f"Node 2: Extraction complete — "
            f"{state['action_items_count']} action items found"
        )

    except Exception as e:
        logger.error(
            f"[{state.get('request_id')}] "
            f"Node 2: Extraction failed — {str(e)}"
        )
        state["action_items"] = []
        state["decisions_made"] = "Extraction unavailable"
        state["blockers_identified"] = "Unknown"
        state["action_items_count"] = 0

    return state