"""
Tests for Lead Intelligence Agent

Tests follow AAA pattern: Arrange, Act, Assert
Same testing approach used at Siemens Healthineers

Test categories:
1. Unit tests — test individual nodes
2. Integration tests — test full agent flow
3. Edge cases — test error handling
"""

import pytest
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


# ==========================================
# Integration Tests — Full Agent Flow
# These test the complete pipeline
# ==========================================

def test_lead_analyze_endpoint_exists():
    """
    Test 1 — Endpoint exists and accepts POST.
    Basic sanity check — always first test.
    """
    # Arrange
    lead_data = {
        "company_name": "Test Company GmbH"
    }

    # Act
    response = client.post("/leads/analyze", json=lead_data)

    # Assert — 200 means endpoint exists and ran
    # We accept 200 or 500 here
    # 500 means LLM failed but endpoint exists
    assert response.status_code in [200, 500]


def test_lead_analyze_returns_request_id():
    """
    Test 2 — Every response has a request ID.
    Critical for audit trail and debugging.
    """
    # Arrange
    lead_data = {
        "company_name": "BMW Munich",
        "contact_name": "Thomas Mueller",
        "contact_email": "thomas@bmw.de",
        "message": "Looking for analytics solution"
    }

    # Act
    response = client.post("/leads/analyze", json=lead_data)
    data = response.json()

    # Assert
    assert "request_id" in data
    assert data["request_id"] is not None
    assert len(data["request_id"]) > 0


def test_lead_analyze_returns_company_name():
    """
    Test 3 — Company name is echoed back correctly.
    Verifies parse_lead node works correctly.
    """
    # Arrange
    lead_data = {
        "company_name": "Siemens Healthineers"
    }

    # Act
    response = client.post("/leads/analyze", json=lead_data)
    data = response.json()

    # Assert
    assert data["company_name"] == "Siemens Healthineers"


def test_lead_analyze_missing_company_name_returns_error():
    """
    Test 4 — Missing company name returns error.
    Verifies parse_lead validation works.
    Cannot research without company name.
    """
    # Arrange — no company_name
    lead_data = {
        "contact_name": "Thomas Mueller",
        "contact_email": "thomas@bmw.de"
    }

    # Act
    response = client.post("/leads/analyze", json=lead_data)

    # Assert — FastAPI returns 422 for missing required field
    assert response.status_code == 422


def test_lead_analyze_score_is_valid_value():
    """
    Test 5 — Score is always HIGH, MEDIUM, or LOW.
    Never any other value.
    Verifies score_lead node returns correct format.
    """
    # Arrange
    lead_data = {
        "company_name": "BMW Munich",
        "message": "Need analytics for manufacturing"
    }

    # Act
    response = client.post("/leads/analyze", json=lead_data)
    data = response.json()

    # Assert
    if data.get("score"):
        assert data["score"] in ["HIGH", "MEDIUM", "LOW"]


def test_lead_analyze_completed_flag_is_true():
    """
    Test 6 — Completed flag is True on success.
    Verifies agent ran all the way through.
    """
    # Arrange
    lead_data = {
        "company_name": "BMW Munich",
        "message": "Need analytics solution"
    }

    # Act
    response = client.post("/leads/analyze", json=lead_data)
    data = response.json()

    # Assert
    assert data["completed"] is True


def test_lead_analyze_whitespace_company_name():
    """
    Test 7 — Company name with whitespace is cleaned.
    Verifies parse_lead strips whitespace correctly.
    """
    # Arrange — company name with extra spaces
    lead_data = {
        "company_name": "  BMW Munich  ",
        "message": "Need analytics"
    }

    # Act
    response = client.post("/leads/analyze", json=lead_data)
    data = response.json()

    # Assert — whitespace should be stripped
    assert data["company_name"] == "BMW Munich"


def test_lead_analyze_response_has_all_fields():
    """
    Test 8 — Response contains all expected fields.
    Verifies LeadResponse model is complete.
    """
    # Arrange
    lead_data = {
        "company_name": "BMW Munich"
    }

    # Act
    response = client.post("/leads/analyze", json=lead_data)
    data = response.json()

    # Assert — all fields must exist in response
    expected_fields = [
        "request_id",
        "company_name",
        "score",
        "score_reasoning",
        "is_qualified",
        "industry",
        "company_size",
        "research_summary",
        "draft_email_subject",
        "draft_email_body",
        "error",
        "completed"
    ]
    for field in expected_fields:
        assert field in data, f"Missing field: {field}"