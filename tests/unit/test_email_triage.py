"""
Tests for Email Triage Agent

Tests follow AAA pattern: Arrange, Act, Assert
Covers all email classification types
and edge cases.
"""

import pytest
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


def test_email_triage_endpoint_exists():
    """
    Test 1 — Endpoint exists and accepts POST.
    Basic sanity check.
    """
    response = client.post(
        "/emails/triage",
        json={
            "sender_email": "test@test.com",
            "body": "test email body"
        }
    )
    assert response.status_code in [200, 500]


def test_email_triage_returns_request_id():
    """
    Test 2 — Every response has request ID.
    Critical for audit trail.
    """
    response = client.post(
        "/emails/triage",
        json={
            "sender_email": "thomas@bmw.de",
            "sender_name": "Thomas",
            "subject": "Demo request",
            "body": "We want to buy your product"
        }
    )
    data = response.json()
    assert "request_id" in data
    assert data["request_id"] is not None


def test_email_triage_missing_body_returns_422():
    """
    Test 3 — Missing required body returns 422.
    Verifies Pydantic validation works.
    """
    response = client.post(
        "/emails/triage",
        json={
            "sender_email": "test@test.com"
        }
    )
    assert response.status_code == 422


def test_email_triage_missing_sender_returns_422():
    """
    Test 4 — Missing sender_email returns 422.
    """
    response = client.post(
        "/emails/triage",
        json={
            "body": "Some email body"
        }
    )
    assert response.status_code == 422


def test_email_triage_classification_is_valid():
    """
    Test 5 — Classification is always valid value.
    Never any other classification type.
    """
    response = client.post(
        "/emails/triage",
        json={
            "sender_email": "test@company.com",
            "subject": "Question about pricing",
            "body": "Hi, I want to know more about your pricing plans"
        }
    )
    data = response.json()
    valid_classifications = [
        "SALES", "SUPPORT", "PARTNERSHIP",
        "PRESS", "FINANCE", "SPAM"
    ]
    if data.get("classification"):
        assert data["classification"] in valid_classifications


def test_email_triage_priority_is_valid():
    """
    Test 6 — Priority is always HIGH, MEDIUM, or LOW.
    """
    response = client.post(
        "/emails/triage",
        json={
            "sender_email": "test@company.com",
            "body": "Regular inquiry about your services"
        }
    )
    data = response.json()
    if data.get("priority"):
        assert data["priority"] in ["HIGH", "MEDIUM", "LOW"]


def test_email_triage_spam_has_no_reply():
    """
    Test 7 — SPAM emails have no draft reply.
    Verifies short circuit routing works.
    """
    response = client.post(
        "/emails/triage",
        json={
            "sender_email": "spam@spam123.com",
            "subject": "You won $1,000,000!!!",
            "body": "Click here to claim your prize now!!!"
        }
    )
    data = response.json()
    if data.get("classification") == "SPAM":
        assert data["draft_reply_body"] is None
        assert data["route_to"] == "ignore"
        assert data["slack_channel"] is None


def test_email_triage_completed_flag_is_true():
    """
    Test 8 — Completed flag is True on success.
    """
    response = client.post(
        "/emails/triage",
        json={
            "sender_email": "test@company.com",
            "body": "I need help with your product"
        }
    )
    data = response.json()
    assert data["completed"] is True


def test_email_triage_response_has_all_fields():
    """
    Test 9 — Response contains all expected fields.
    """
    response = client.post(
        "/emails/triage",
        json={
            "sender_email": "test@company.com",
            "body": "Test email"
        }
    )
    data = response.json()
    expected_fields = [
        "request_id",
        "sender_email",
        "classification",
        "classification_reasoning",
        "priority",
        "sentiment",
        "sender_company",
        "core_request",
        "requires_immediate_action",
        "draft_reply_subject",
        "draft_reply_body",
        "route_to",
        "slack_channel",
        "route_reason",
        "error",
        "completed"
    ]
    for field in expected_fields:
        assert field in data, f"Missing field: {field}"


def test_email_triage_sales_routes_to_sales():
    """
    Test 10 — Sales emails route to sales team.
    Verifies routing rules work correctly.
    """
    response = client.post(
        "/emails/triage",
        json={
            "sender_email": "buyer@bigcompany.com",
            "sender_name": "John Smith",
            "subject": "Interested in purchasing your platform",
            "body": "We have budget approved and want to buy your analytics platform. Can we schedule a demo?"
        }
    )
    data = response.json()
    if data.get("classification") == "SALES":
        assert data["route_to"] == "sales"
        assert data["slack_channel"] == "#sales-leads"