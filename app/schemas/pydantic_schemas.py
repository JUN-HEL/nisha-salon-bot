"""Pydantic v2 request / response schemas."""
from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field


# ─── WhatsApp Webhook Payloads ─────────────────────────────────────────────────

class WhatsAppTextBody(BaseModel):
    body: str


class WhatsAppMessage(BaseModel):
    from_: str = Field(alias="from")
    id: str
    timestamp: str
    type: str
    text: Optional[WhatsAppTextBody] = None

    model_config = {"populate_by_name": True}


class WhatsAppContact(BaseModel):
    profile: dict[str, Any]
    wa_id: str


class WhatsAppValue(BaseModel):
    messaging_product: str
    metadata: dict[str, Any]
    contacts: Optional[list[WhatsAppContact]] = None
    messages: Optional[list[WhatsAppMessage]] = None
    statuses: Optional[list[dict[str, Any]]] = None


class WhatsAppChange(BaseModel):
    value: WhatsAppValue
    field: str


class WhatsAppEntry(BaseModel):
    id: str
    changes: list[WhatsAppChange]


class WhatsAppWebhookPayload(BaseModel):
    object: str
    entry: list[WhatsAppEntry]


# ─── Send Message ──────────────────────────────────────────────────────────────

class SendMessageRequest(BaseModel):
    phone: str = Field(..., description="Recipient phone number with country code")
    message: str = Field(..., description="Text message to send")


class SendMessageResponse(BaseModel):
    success: bool
    message_id: Optional[str] = None
    error: Optional[str] = None


# ─── Customer ──────────────────────────────────────────────────────────────────

class CustomerResponse(BaseModel):
    phone: str
    name: Optional[str]
    preferences: Optional[str]
    favorite_service: Optional[str]
    preferred_stylist: Optional[str]
    visit_count: int
    last_visit: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Appointment ───────────────────────────────────────────────────────────────

class AppointmentResponse(BaseModel):
    name: str
    phone: str
    service: str
    stylist: Optional[str]
    date: str
    time: str
    status: str


# ─── Health ────────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    environment: str
    version: str = "1.0.0"
