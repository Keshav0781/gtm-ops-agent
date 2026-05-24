"""
Tests for main.py — API entry point
Tests follow AAA pattern: Arrange, Act, Assert
Same testing approach used at Siemens Healthineers
"""

import pytest
from fastapi.testclient import TestClient
from api.main import app

# TestClient simulates HTTP requests without
# needing a real running server
# At Siemens they use same TestClient pattern
client = TestClient(app)


def test_health_endpoint_returns_200():
    """
    Test 1 — Health check returns 200 status.
    This is what Railway/Azure checks every 30 seconds.
    If this fails — service would be restarted automatically.
    """
    # Arrange — client is already set up above

    # Act — call the health endpoint
    response = client.get("/health")

    # Assert — verify status code is 200
    assert response.status_code == 200


def test_health_endpoint_returns_correct_data():
    """
    Test 2 — Health check returns correct response body.
    Verifies our health response has all required fields.
    """
    # Act
    response = client.get("/health")

    # Assert — verify response body
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "gtm-ops-agent"
    assert data["version"] == "1.0.0"


def test_root_endpoint_returns_200():
    """
    Test 3 — Root endpoint returns 200 status.
    Verifies service is accessible.
    """
    # Act
    response = client.get("/")

    # Assert
    assert response.status_code == 200


def test_root_endpoint_returns_correct_data():
    """
    Test 4 — Root endpoint returns correct service info.
    Verifies service metadata is correct.
    """
    # Act
    response = client.get("/")

    # Assert
    data = response.json()
    assert data["service"] == "GTM Ops Agent"
    assert data["version"] == "1.0.0"
    assert data["status"] == "running"
    assert data["docs"] == "/docs"