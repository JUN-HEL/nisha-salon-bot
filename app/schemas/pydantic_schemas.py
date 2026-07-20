
"""Pydantic v2 request / response schemas."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# ─── WhatsApp Webhook Payloads ────────────────────────────────────────────────


class WhatsAppTextBody(BaseModel):
    body: str


class WhatsAppMessage(BaseModel):
    from_: str = Field(alias="from")
    id: str
    timestamp: Optional[str] = None
    type: str
    text: Optional[WhatsAppTextBody] = None

    model_config = {
        "populate_by_name": True
    }


class WhatsAppContact(BaseModel):
    profile: Optional[dict[str, Any]] = None
    wa_id: Optional[str] = None


class WhatsAppStatus(BaseModel):
    id: Optional[str] = None
    status: Optional[str] = None
    timestamp: Optional[str] = None
    recipient_id: Optional[str] = None


class WhatsAppValue(BaseModel):
    messaging_product: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None

    contacts: Optional[list[WhatsAppContact]] = None
    messages: Optional[list[WhatsAppMessage]] = None
    statuses: Optional[list[WhatsAppStatus]] = None


class WhatsAppChange(BaseModel):
    value: WhatsAppValue
    field: Optional[str] = None


class WhatsAppEntry(BaseModel):
    id: Optional[str] = None
    changes: list[WhatsAppChange]


class WhatsAppWebhookPayload(BaseModel):
    object: Optional[str] = None
    entry: list[WhatsAppEntry]


# ─── Send Message ─────────────────────────────────────────────────────────────


class SendMessageRequest(BaseModel):
    phone: str = Field(
        ...,
        description="Recipient phone number with country code"
    )

    message: str = Field(
        ...,
        description="Text message to send"
    )


class SendMessageResponse(BaseModel):
    success: bool
    message_id: Optional[str] = None
    error: Optional[str] = None


# ─── Customer ────────────────────────────────────────────────────────────────


class CustomerResponse(BaseModel):
    phone: str
    name: Optional[str] = None
    preferences: Optional[str] = None
    favorite_service: Optional[str] = None
    preferred_stylist: Optional[str] = None
    visit_count: int
    last_visit: Optional[datetime] = None
    created_at: datetime

    model_config = {
        "from_attributes": True
    }


# ─── Appointment ─────────────────────────────────────────────────────────────


class AppointmentResponse(BaseModel):
    name: str
    phone: str
    service: str
    stylist: Optional[str] = None
    date: str
    time: str
    status: str


# ─── Health ──────────────────────────────────────────────────────────────────


class HealthResponse(BaseModel):
    status: str
    environment: str
    version: str = "1.0.0"