"""Unit tests for webhook endpoints."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient

# We need to patch external clients before importing the app
with (
    patch("app.ai.gemini_client.genai"),
    patch("app.database.session.create_async_engine"),
):
    from main import app

client = TestClient(app)


def test_root():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["salon"] == "Nisha Hair Salon"
    assert data["status"] == "online"


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_webhook_verification_success():
    response = client.get(
        "/webhook",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "nisha_salon_verify",
            "hub.challenge": "test_challenge_123",
        },
    )
    assert response.status_code == 200
    assert response.text == "test_challenge_123"


def test_webhook_verification_wrong_token():
    response = client.get(
        "/webhook",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "wrong_token",
            "hub.challenge": "abc",
        },
    )
    assert response.status_code == 403
