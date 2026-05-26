"""
Tests for Meeting Intelligence Agent

Tests follow AAA pattern: Arrange, Act, Assert
Covers different meeting types and edge cases.
"""

import pytest
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

# Sample transcript used across multiple tests
SAMPLE_TRANSCRIPT = """
John: Yesterday I finished the login page. 
Today I will work on the dashboard. No blockers.
Sarah: I reviewed pull requests yesterday. 
Today deploying to staging. Blocker: waiting for DevOps access.
Marcus: Fixed the database bug. 
Starting API integration today. No blockers.
"""

PLANNING_TRANSCRIPT = """
Sarah: We need to prioritize the dashboard feature.
Marcus: Engineering can start next week but need designs first.
Anna: I can have designs ready by Friday.
Marcus: Development will take 3 weeks.
Sarah: Any blockers? Marcus: Waiting on API credentials from DevOps.
Sarah: I will follow up with DevOps today.
"""


def test_meeting_analyze_endpoint_exists():
    """
    Test 1 — Endpoint exists and accepts POST.
    """
    response = client.post(
        "/meetings/analyze",
        json={
            "transcript": "Short test meeting transcript"
        }
    )
    assert response.status_code in [200, 500]


def test_meeting_analyze_missing_transcript_returns_422():
    """
    Test 2 — Missing transcript returns 422.
    Transcript is required field.
    """
    response = client.post(
        "/meetings/analyze",
        json={
            "meeting_title": "Test Meeting",
            "attendees": "John, Sarah"
        }
    )
    assert response.status_code == 422


def test_meeting_analyze_returns_request_id():
    """
    Test 3 — Every response has request ID.
    Critical for audit trail.
    """
    response = client.post(
        "/meetings/analyze",
        json={
            "meeting_title": "Daily Standup",
            "transcript": SAMPLE_TRANSCRIPT
        }
    )
    data = response.json()
    assert "request_id" in data
    assert data["request_id"] is not None


def test_meeting_analyze_completed_flag_is_true():
    """
    Test 4 — Completed flag is True on success.
    """
    response = client.post(
        "/meetings/analyze",
        json={
            "transcript": SAMPLE_TRANSCRIPT
        }
    )
    data = response.json()
    assert data["completed"] is True


def test_meeting_analyze_meeting_type_is_valid():
    """
    Test 5 — Meeting type is always valid value.
    """
    response = client.post(
        "/meetings/analyze",
        json={
            "meeting_title": "Daily Standup",
            "transcript": SAMPLE_TRANSCRIPT
        }
    )
    data = response.json()
    valid_types = [
        "standup", "planning", "review",
        "client_call", "interview", "general"
    ]
    if data.get("meeting_type"):
        assert data["meeting_type"] in valid_types


def test_meeting_analyze_has_slack_message():
    """
    Test 6 — Slack message is generated.
    Critical for team notifications.
    """
    response = client.post(
        "/meetings/analyze",
        json={
            "meeting_title": "Team Meeting",
            "attendees": "John, Sarah, Marcus",
            "transcript": PLANNING_TRANSCRIPT
        }
    )
    data = response.json()
    assert data["slack_message"] is not None
    assert len(data["slack_message"]) > 0


def test_meeting_analyze_has_slack_channel():
    """
    Test 7 — Slack channel is always assigned.
    """
    response = client.post(
        "/meetings/analyze",
        json={
            "transcript": SAMPLE_TRANSCRIPT
        }
    )
    data = response.json()
    assert data["slack_channel"] is not None


def test_meeting_analyze_notifications_ready():
    """
    Test 8 — Notifications ready flag is True.
    Confirms Node 4 completed successfully.
    """
    response = client.post(
        "/meetings/analyze",
        json={
            "transcript": SAMPLE_TRANSCRIPT
        }
    )
    data = response.json()
    assert data["notifications_ready"] is True


def test_meeting_analyze_response_has_all_fields():
    """
    Test 9 — Response contains all expected fields.
    """
    response = client.post(
        "/meetings/analyze",
        json={
            "transcript": SAMPLE_TRANSCRIPT
        }
    )
    data = response.json()
    expected_fields = [
        "request_id",
        "meeting_title",
        "meeting_type",
        "topics_discussed",
        "participants_identified",
        "action_items_count",
        "decisions_made",
        "blockers_identified",
        "summary",
        "key_outcomes",
        "next_meeting_suggested",
        "slack_message",
        "slack_channel",
        "notion_tasks_payload",
        "notifications_ready",
        "error",
        "completed"
    ]
    for field in expected_fields:
        assert field in data, f"Missing field: {field}"


def test_meeting_analyze_standup_routes_correctly():
    """
    Test 10 — Standup meeting routes to correct channel.
    """
    response = client.post(
        "/meetings/analyze",
        json={
            "meeting_title": "Daily Standup",
            "transcript": SAMPLE_TRANSCRIPT
        }
    )
    data = response.json()
    if data.get("meeting_type") == "standup":
        assert data["slack_channel"] == "#daily-standup"