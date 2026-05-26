"""
Node 4 — Prepare Notifications

Final node in Meeting Intelligence Agent.
Formats all extracted information into
ready-to-send Slack message and Notion
tasks payload.

This node does NOT send anything.
It only prepares the formatted content.
Actual sending happens in n8n after
human approval — Phase 8.


Business value:
Team gets complete meeting summary in Slack
within 5 minutes of meeting ending.
All action items automatically queued
for Notion task creation.
Zero manual work required.
"""

import json
import logging
from agents.meeting_intelligence.state import MeetingState

logger = logging.getLogger(__name__)

# Slack channel routing based on meeting type
CHANNEL_ROUTING = {
    "standup": "#daily-standup",
    "planning": "#sprint-planning",
    "review": "#team-updates",
    "client_call": "#sales-updates",
    "interview": "#hiring",
    "general": "#team-updates"
}


def format_slack_message(state: MeetingState) -> str:
    """
    Formats complete Slack message from meeting data.
    Uses Slack markdown formatting for readability.

    Why not use LLM here?
    Slack message formatting is deterministic.
    Same data should always produce same format.
    No creativity needed — just structure.
    LLM would add unnecessary variability and cost.


    """
    action_items = state.get("action_items", [])
    action_items_count = state.get("action_items_count", 0)

    # Build action items section
    action_items_text = ""
    if action_items:
        action_items_text = "\n*Action Items:*\n"
        for i, item in enumerate(action_items, 1):
            owner = item.get("owner") or "Unassigned"
            deadline = item.get("deadline") or "No deadline"
            priority = item.get("priority", "medium").upper()
            action_items_text += (
                f"{i}. {item.get('task', 'Task')} "
                f"— Owner: {owner} "
                f"| Due: {deadline} "
                f"| Priority: {priority}\n"
            )
    else:
        action_items_text = "\n*Action Items:* None identified\n"

    # Build complete Slack message
    message = f"""
*Meeting Summary — {state.get('meeting_title', 'Team Meeting')}*
Date: {state.get('meeting_date', 'Unknown')} | Type: {state.get('meeting_type', 'General').title()} | Attendees: {state.get('attendees', 'Not specified')}

*Summary:*
{state.get('summary', 'No summary available')}

*Key Outcomes:*
{state.get('key_outcomes', 'No outcomes recorded')}
{action_items_text}
*Decisions Made:*
{state.get('decisions_made', 'No decisions recorded')}

*Blockers:*
{state.get('blockers_identified', 'None identified')}

*Next Meeting:* {state.get('next_meeting_suggested', 'None scheduled')}

_{action_items_count} action item(s) queued for Notion_
    """.strip()

    return message


def format_notion_payload(state: MeetingState) -> str:
    """
    Formats action items as Notion tasks payload.
    Returns JSON string ready for Notion API.

    Each action item becomes one Notion task
    with title, assignee, due date, and priority.
    """
    action_items = state.get("action_items", [])
    meeting_title = state.get(
        "meeting_title", "Team Meeting"
    )

    notion_tasks = []
    for item in action_items:
        task = {
            "title": item.get("task", "Untitled task"),
            "assignee": item.get("owner"),
            "due_date": item.get("deadline"),
            "priority": item.get("priority", "medium"),
            "source_meeting": meeting_title,
            "meeting_date": state.get("meeting_date")
        }
        notion_tasks.append(task)

    return json.dumps(notion_tasks, indent=2)


def prepare_notifications(
    state: MeetingState
) -> MeetingState:
    """
    Node 4 — Prepare Slack and Notion notifications.

    Note: This node is NOT async.
    No LLM call needed — pure formatting logic.
    Same reasoning as route_email in Email Triage —
    deterministic operations do not need LLM.

    What it does:
    1. Checks if previous nodes failed
    2. Determines correct Slack channel
    3. Formats Slack message
    4. Formats Notion tasks payload
    5. Marks notifications as ready
    6. Marks agent as completed

    Input state fields used:
        meeting_title, meeting_date, meeting_type,
        attendees, summary, key_outcomes,
        action_items, decisions_made,
        blockers_identified, next_meeting_suggested

    Output state fields added:
        slack_message, notion_tasks_payload,
        slack_channel, notifications_ready, completed
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

    logger.info(
        f"[{state.get('request_id')}] "
        f"Node 4: Preparing notifications for "
        f"{state.get('meeting_title', 'Untitled Meeting')}"
    )

    # ==========================================
    # Step 2 — Determine Slack channel
    # ==========================================
    meeting_type = state.get("meeting_type", "general")
    state["slack_channel"] = CHANNEL_ROUTING.get(
        meeting_type,
        "#team-updates"
    )

    # ==========================================
    # Step 3 — Format Slack message
    # ==========================================
    state["slack_message"] = format_slack_message(state)

    # ==========================================
    # Step 4 — Format Notion tasks payload
    # ==========================================
    state["notion_tasks_payload"] = format_notion_payload(
        state
    )

    # ==========================================
    # Step 5 — Mark notifications as ready
    # ==========================================
    state["notifications_ready"] = True
    state["completed"] = True

    logger.info(
        f"[{state.get('request_id')}] "
        f"Node 4: Notifications ready — "
        f"channel={state['slack_channel']} "
        f"tasks={state.get('action_items_count', 0)}"
    )

    return state