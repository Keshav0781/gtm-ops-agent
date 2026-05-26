"""
Tests for CRM Hygiene Agent

Tests follow AAA pattern: Arrange, Act, Assert
Covers deal scanning, alert generation,
and edge cases.
"""

import pytest
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

# Sample deals used across tests
SAMPLE_DEALS = [
    {
        "deal_id": "deal_001",
        "deal_name": "BMW Munich Enterprise",
        "company": "BMW Munich",
        "owner": "John",
        "stage": "Proposal Sent",
        "deal_value": 50000,
        "contact_email": "thomas@bmw.de",
        "contact_phone": "+49891234567",
        "last_contact_date": "2026-05-01",
        "stage_changed_date": "2026-05-01"
    },
    {
        "deal_id": "deal_002",
        "deal_name": "Berlin Startup Deal",
        "company": "TechCo Berlin",
        "owner": "Sarah",
        "stage": "First Contact",
        "deal_value": 12000,
        "contact_email": "info@techco.de",
        "last_contact_date": "2026-05-26",
        "stage_changed_date": "2026-05-26"
    }
]

STALE_DEAL = {
    "deal_id": "deal_stale",
    "deal_name": "Stale Deal",
    "company": "OldCompany GmbH",
    "owner": "John",
    "stage": "First Contact",
    "deal_value": 10000,
    "contact_email": "old@company.de",
    "contact_phone": "+49123456",
    "last_contact_date": "2026-04-01",
    "stage_changed_date": "2026-04-01"
}

INCOMPLETE_DEAL = {
    "deal_id": "deal_incomplete",
    "deal_name": "Incomplete Deal",
    "company": "NoContact GmbH",
    "owner": "Marcus",
    "stage": "First Contact",
    "last_contact_date": "2026-05-26"
}


def test_crm_analyze_endpoint_exists():
    """
    Test 1 — Endpoint exists and accepts POST.
    """
    response = client.post(
        "/crm/analyze",
        json={"deals": SAMPLE_DEALS}
    )
    assert response.status_code in [200, 500]


def test_crm_analyze_missing_deals_returns_422():
    """
    Test 2 — Missing deals returns 422.
    """
    response = client.post(
        "/crm/analyze",
        json={}
    )
    assert response.status_code == 422


def test_crm_analyze_returns_request_id():
    """
    Test 3 — Every response has request ID.
    """
    response = client.post(
        "/crm/analyze",
        json={"deals": SAMPLE_DEALS}
    )
    data = response.json()
    assert "request_id" in data
    assert data["request_id"] is not None


def test_crm_analyze_completed_flag_is_true():
    """
    Test 4 — Completed flag is True on success.
    """
    response = client.post(
        "/crm/analyze",
        json={"deals": SAMPLE_DEALS}
    )
    data = response.json()
    assert data["completed"] is True


def test_crm_analyze_counts_deals_correctly():
    """
    Test 5 — Total deals count matches input.
    """
    response = client.post(
        "/crm/analyze",
        json={"deals": SAMPLE_DEALS}
    )
    data = response.json()
    assert data["total_deals_count"] == len(SAMPLE_DEALS)


def test_crm_analyze_stale_deal_detected():
    """
    Test 6 — Stale deal is detected and flagged.
    Deal with last contact April 1 should be flagged.
    """
    response = client.post(
        "/crm/analyze",
        json={"deals": [STALE_DEAL]}
    )
    data = response.json()
    assert data["total_alerts_count"] > 0
    assert data["high_priority_count"] > 0


def test_crm_analyze_incomplete_deal_detected():
    """
    Test 7 — Incomplete deal missing fields is flagged.
    """
    response = client.post(
        "/crm/analyze",
        json={"deals": [INCOMPLETE_DEAL]}
    )
    data = response.json()
    assert data["total_alerts_count"] > 0


def test_crm_analyze_owner_notifications_grouped():
    """
    Test 8 — Notifications grouped by owner.
    Each owner gets one consolidated message.
    """
    response = client.post(
        "/crm/analyze",
        json={"deals": [STALE_DEAL, INCOMPLETE_DEAL]}
    )
    data = response.json()
    notifications = data.get("owner_notifications", {})
    assert "John" in notifications
    assert "Marcus" in notifications


def test_crm_analyze_scan_summary_exists():
    """
    Test 9 — Scan summary is always generated.
    """
    response = client.post(
        "/crm/analyze",
        json={"deals": SAMPLE_DEALS}
    )
    data = response.json()
    assert data["scan_summary"] is not None
    assert len(data["scan_summary"]) > 0


def test_crm_analyze_response_has_all_fields():
    """
    Test 10 — Response contains all expected fields.
    """
    response = client.post(
        "/crm/analyze",
        json={"deals": SAMPLE_DEALS}
    )
    data = response.json()
    expected_fields = [
        "request_id",
        "scan_date",
        "total_deals_count",
        "healthy_deals_count",
        "problematic_deals_count",
        "total_alerts_count",
        "high_priority_count",
        "medium_priority_count",
        "low_priority_count",
        "owner_notifications",
        "scan_summary",
        "error",
        "completed"
    ]
    for field in expected_fields:
        assert field in data, f"Missing field: {field}"