
"""Pydantic v2 request / response schemas."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, ConfigDict


# ─── Base Config ──────────────────────────────────────────────────────────────

class WhatsAppBaseModel(BaseModel):
    """
    Base model for WhatsApp payloads.
    Meta can add new fields, so allow unknown fields.
    """

    model_config = ConfigDict(
        extra="allow",
        populate_by_name=True
    )


# ─── WhatsApp Webhook Payloads ────────────────────────────────────────────────


class WhatsAppTextBody(WhatsAppBaseModel):
    body: Optional[str] = None


class WhatsAppMessage(WhatsAppBaseModel):
    from_: Optional[str] = Field(
        default=None,
        alias="from"
    )

    id: Optional[str] = None
    timestamp: Optional[str] = None
    type: Optional[str] = None
    text: Optional[WhatsAppTextBody] = None


class WhatsAppContact(WhatsAppBaseModel):
    profile: Optional[dict[str, Any]] = None
    wa_id: Optional[str] = None


class WhatsAppStatus(WhatsAppBaseModel):
    id: Optional[str] = None
    status: Optional[str] = None
    timestamp: Optional[str] = None
    recipient_id: Optional[str] = None


class WhatsAppMetadata(WhatsAppBaseModel):
    display_phone_number: Optional[str] = None
    phone_number_id: Optional[str] = None


class WhatsAppValue(WhatsAppBaseModel):
    messaging_product: Optional[str] = None

    metadata: Optional[WhatsAppMetadata] = None

    contacts: Optional[list[WhatsAppContact]] = None

    messages: Optional[list[WhatsAppMessage]] = None

    statuses: Optional[list[WhatsAppStatus]] = None


class WhatsAppChange(WhatsAppBaseModel):
    field: Optional[str] = None
    value: Optional[WhatsAppValue] = None


class WhatsAppEntry(WhatsAppBaseModel):
    id: Optional[str] = None
    changes: Optional[list[WhatsAppChange]] = None


class WhatsAppWebhookPayload(WhatsAppBaseModel):
    object: Optional[str] = None
    entry: Optional[list[WhatsAppEntry]] = None


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

    model_config = ConfigDict(
        from_attributes=True
    )


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
