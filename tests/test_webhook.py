"""Unit tests for webhook endpoints."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from app.database.session import get_db

# Patch external services before importing app
with (
    patch("app.ai.gemini_client.genai"),
    patch("app.database.session.create_async_engine"),
):
    from main import app


client = TestClient(app)


# ─────────────────────────────────────────────
# Mock database dependency
# ─────────────────────────────────────────────

@pytest.fixture
def mock_db():
    db = AsyncMock()

    history_item = MagicMock()
    history_item.role = "user"
    history_item.message = "Hello"

    result = MagicMock()
    result.scalars.return_value.all.return_value = [history_item]

    db.execute.return_value = result

    return db


@pytest.fixture(autouse=True)
def override_database(mock_db):
    async def fake_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = fake_get_db

    yield

    app.dependency_overrides.clear()


# ─────────────────────────────────────────────
# Root
# ─────────────────────────────────────────────

def test_root():
    response = client.get("/")

    assert response.status_code == 200

    data = response.json()

    assert data["salon"] == "Nisha Hair Salon"
    assert data["status"] == "online"


# ─────────────────────────────────────────────
# Health
# ─────────────────────────────────────────────

def test_health():
    response = client.get("/health")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "healthy"


# ─────────────────────────────────────────────
# GET webhook verification
# ─────────────────────────────────────────────

def test_webhook_verification_success():

    response = client.get(
        "/webhook",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "salon63974610.,",
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


# ─────────────────────────────────────────────
# POST webhook - success
# ─────────────────────────────────────────────

@patch("app.webhook.get_gemini_client")
@patch("app.webhook.get_whatsapp_client")
def test_receive_message_success(
    mock_whatsapp,
    mock_gemini,
):

    whatsapp = AsyncMock()
    whatsapp.mark_as_read = AsyncMock()
    whatsapp.send_text_message = AsyncMock()

    mock_whatsapp.return_value = whatsapp


    gemini = AsyncMock()
    gemini.generate_response.return_value = "Hello! How can I help?"

    mock_gemini.return_value = gemini


    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "entry1",
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {},
                            "messages": [
                                {
                                    "from": "919876543210",
                                    "id": "wamid123",
                                    "timestamp": "123456",
                                    "type": "text",
                                    "text": {
                                        "body": "Hello"
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
        ]
    }


    response = client.post(
        "/webhook",
        json=payload
    )


    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

    whatsapp.mark_as_read.assert_awaited_once_with(
        "wamid123"
    )

    whatsapp.send_text_message.assert_awaited_once_with(
        "919876543210",
        "Hello! How can I help?"
    )

    gemini.generate_response.assert_awaited_once()


# ─────────────────────────────────────────────
# POST webhook - Gemini error
# ─────────────────────────────────────────────

@patch("app.webhook.get_gemini_client")
@patch("app.webhook.get_whatsapp_client")
def test_receive_message_gemini_error(
    mock_whatsapp,
    mock_gemini,
):

    whatsapp = AsyncMock()
    whatsapp.send_text_message = AsyncMock()

    mock_whatsapp.return_value = whatsapp


    gemini = AsyncMock()
    gemini.generate_response.side_effect = Exception(
        "Gemini failed"
    )

    mock_gemini.return_value = gemini


    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "entry1",
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {},
                            "messages": [
                                {
                                    "from": "919876543210",
                                    "id": "msg1",
                                    "timestamp": "123",
                                    "type": "text",
                                    "text": {
                                        "body": "Hi"
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
        ]
    }


    response = client.post(
        "/webhook",
        json=payload
    )


    assert response.status_code == 200

    whatsapp.send_text_message.assert_awaited_once()

    sent_message = (
        whatsapp.send_text_message
        .await_args
        .args[1]
    )

    assert "I'm sorry" in sent_message


# ─────────────────────────────────────────────
# POST webhook - ignore images
# ─────────────────────────────────────────────

@patch("app.webhook.get_gemini_client")
def test_receive_message_ignore_non_text(
    mock_gemini,
):

    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "entry1",
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {},
                            "messages": [
                                {
                                    "from": "919876543210",
                                    "id": "img123",
                                    "timestamp": "123",
                                    "type": "image"
                                }
                            ]
                        }
                    }
                ]
            }
        ]
    }


    response = client.post(
        "/webhook",
        json=payload
    )


    assert response.status_code == 200

    mock_gemini.return_value.generate_response.assert_not_called()