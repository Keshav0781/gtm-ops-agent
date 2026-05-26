"""
Meeting Intelligence Agent — State Definition

Shared notebook flowing through all 4 nodes.

Flow:
extract_transcript → extract_action_items →
generate_summary → prepare_notifications

Real business scenario:
Meeting ends at 3pm. By 3:05pm agent has:
- Extracted all action items with owners
- Generated clean summary
- Created Notion tasks automatically
- Posted summary to Slack channel
Team member never needs to write notes again.

"""

from typing import Optional, List
from typing_extensions import TypedDict


class ActionItem(TypedDict):
    """
    Single action item extracted from meeting.
    Structured so it can be directly created
    as a Notion task or Jira ticket.
    """
    task: str
    owner: Optional[str]
    deadline: Optional[str]
    priority: Optional[str]


class MeetingState(TypedDict):
    """
    Complete state for Meeting Intelligence Agent.
    Each node reads from and adds to this state.
    """

    # ==========================================
    # INPUT — meeting information
    # Provided before graph runs
    # In Phase 8 this comes from
    # Google Calendar MCP + Google Drive MCP
    # ==========================================
    meeting_title: Optional[str]
    meeting_date: Optional[str]
    attendees: Optional[str]
    transcript: Optional[str]      # raw meeting transcript
                                   # or notes
    duration_minutes: Optional[int]

    # ==========================================
    # EXTRACTED CONTENT — from extract_transcript
    # Cleaned and structured transcript data
    # ==========================================
    cleaned_transcript: Optional[str]
    topics_discussed: Optional[str]
    participants_identified: Optional[str]
    meeting_type: Optional[str]    # standup, planning,
                                   # review, client call,
                                   # interview

    # ==========================================
    # ACTION ITEMS — from extract_action_items
    # Structured list ready for Notion/Jira
    # ==========================================
    action_items: Optional[List[ActionItem]]
    decisions_made: Optional[str]
    blockers_identified: Optional[str]
    action_items_count: Optional[int]

    # ==========================================
    # SUMMARY — from generate_summary
    # Clean readable summary for Slack
    # ==========================================
    summary: Optional[str]
    key_outcomes: Optional[str]
    next_meeting_suggested: Optional[str]

    # ==========================================
    # NOTIFICATIONS — from prepare_notifications
    # Ready to send to Slack and Notion
    # ==========================================
    slack_message: Optional[str]
    notion_tasks_payload: Optional[str]
    slack_channel: Optional[str]
    notifications_ready: Optional[bool]

    # ==========================================
    # METADATA — tracking and audit
    # ==========================================
    request_id: Optional[str]
    error: Optional[str]
    completed: Optional[bool]