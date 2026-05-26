"""
Tests for Competitor Intelligence Agent

Tests follow AAA pattern: Arrange, Act, Assert
Note: These tests do NOT make real HTTP requests.
They test validation, error handling, and
response structure only.

Real scraping tests would be integration tests
run separately to avoid slow test suite.
"""

import pytest
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


def test_competitor_analyze_endpoint_exists():
    """
    Test 1 — Endpoint exists and accepts POST.
    """
    response = client.post(
        "/competitors/analyze",
        json={
            "competitors": [
                {
                    "name": "TestCompetitor",
                    "url": "https://example.com"
                }
            ]
        }
    )
    assert response.status_code in [200, 500]


def test_competitor_analyze_missing_competitors_returns_422():
    """
    Test 2 — Missing competitors returns 422.
    """
    response = client.post(
        "/competitors/analyze",
        json={}
    )
    assert response.status_code == 422


def test_competitor_analyze_empty_list_returns_error():
    """
    Test 3 — Empty competitors list returns error.
    """
    response = client.post(
        "/competitors/analyze",
        json={"competitors": []}
    )
    data = response.json()
    assert data.get("error") is not None
    assert data.get("completed") is False


def test_competitor_analyze_returns_request_id():
    """
    Test 4 — Every response has request ID.
    """
    response = client.post(
        "/competitors/analyze",
        json={
            "competitors": [
                {
                    "name": "TestCompetitor",
                    "url": "https://example.com"
                }
            ]
        }
    )
    data = response.json()
    assert "request_id" in data
    assert data["request_id"] is not None


def test_competitor_analyze_invalid_competitor_handled():
    """
    Test 5 — Competitor missing name and URL handled.
    """
    response = client.post(
        "/competitors/analyze",
        json={
            "competitors": [
                {
                    "name": "",
                    "url": ""
                }
            ]
        }
    )
    data = response.json()
    assert data.get("error") is not None


def test_competitor_analyze_response_has_all_fields():
    """
    Test 6 — Response contains all expected fields.
    """
    response = client.post(
        "/competitors/analyze",
        json={
            "competitors": [
                {
                    "name": "TestCompetitor",
                    "url": "https://example.com"
                }
            ]
        }
    )
    data = response.json()
    expected_fields = [
        "request_id",
        "report_date",
        "successful_scrapes",
        "failed_scrapes",
        "total_changes_found",
        "competitor_analyses",
        "slack_report",
        "report_summary",
        "slack_channel",
        "report_ready",
        "error",
        "completed"
    ]
    for field in expected_fields:
        assert field in data, f"Missing field: {field}"


def test_competitor_analyze_report_date_set():
    """
    Test 7 — Report date is always set.
    Even when not provided in request.
    """
    response = client.post(
        "/competitors/analyze",
        json={
            "competitors": [
                {
                    "name": "TestCompetitor",
                    "url": "https://example.com"
                }
            ]
        }
    )
    data = response.json()
    assert data.get("report_date") is not None


def test_competitor_analyze_slack_channel_set():
    """
    Test 8 — Slack channel is always set on success.
    """
    response = client.post(
        "/competitors/analyze",
        json={
            "competitors": [
                {
                    "name": "TestCompetitor",
                    "url": "https://example.com"
                }
            ]
        }
    )
    data = response.json()
    if data.get("completed"):
        assert data.get("slack_channel") == (
            "#competitive-intelligence"
        )