"""Application entry point — FastAPI app factory and route registration."""
import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

from app.config import get_settings
from app.database.session import init_db, close_db, get_db
from app.models.db_models import Customer, ConversationMemory
from app.schemas.pydantic_schemas import (
    HealthResponse,
    CustomerResponse,
    AppointmentResponse,
    SendMessageRequest,
    SendMessageResponse,
)
from app.sheets.client import get_sheets_client
from app.whatsapp.client import get_whatsapp_client
from app.webhook import router as webhook_router
from app.utils.logger import configure_logging, logger

# Create logs directory
os.makedirs("logs", exist_ok=True)
configure_logging()

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info("🌸 Nisha Hair Salon Bot starting up…")
    await init_db()
    yield
    await close_db()
    logger.info("👋 Nisha Hair Salon Bot shut down cleanly")


app = FastAPI(
    title="Nisha Hair Salon — AI WhatsApp Assistant",
    description=(
        "Production-ready WhatsApp chatbot powered by Google Gemini 2.5 Flash. "
        "Handles bookings, FAQs, service info, and customer memory."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Webhook routes ─────────────────────────────────────────────────────────────
app.include_router(webhook_router, tags=["Webhook"])


# ─── Root ───────────────────────────────────────────────────────────────────────
@app.get("/", tags=["General"])
async def root() -> dict:
    return {
        "salon": "Nisha Hair Salon",
        "assistant": "Priya — AI Receptionist",
        "status": "online",
        "docs": "/docs",
    }


# ─── Health ─────────────────────────────────────────────────────────────────────
@app.get("/health", response_model=HealthResponse, tags=["General"])
async def health() -> HealthResponse:
    return HealthResponse(
        status="healthy",
        environment=settings.app_env,
    )


# ─── Send message (manual / admin trigger) ──────────────────────────────────────
@app.post("/send-message", response_model=SendMessageResponse, tags=["Admin"])
async def send_message(req: SendMessageRequest) -> SendMessageResponse:
    try:
        msg_id = await get_whatsapp_client().send_text_message(req.phone, req.message)
        return SendMessageResponse(success=True, message_id=msg_id)
    except Exception as exc:
        logger.error("Manual send-message error", error=str(exc))
        return SendMessageResponse(success=False, error=str(exc))


# ─── Customers (admin view) ──────────────────────────────────────────────────────
@app.get("/customers", response_model=list[CustomerResponse], tags=["Admin"])
async def list_customers(db: AsyncSession = Depends(get_db)) -> list[CustomerResponse]:
    result = await db.execute(select(Customer).order_by(Customer.created_at.desc()))
    return [CustomerResponse.model_validate(c) for c in result.scalars().all()]


# ─── Appointments (admin view) ───────────────────────────────────────────────────
@app.get("/appointments", response_model=list[AppointmentResponse], tags=["Admin"])
async def list_appointments() -> list[AppointmentResponse]:
    try:
        raw = get_sheets_client().get_appointments()
        return [
            AppointmentResponse(
                name=r.get("Name", ""),
                phone=str(r.get("Phone", "")),
                service=r.get("Service", ""),
                stylist=r.get("Stylist", ""),
                date=str(r.get("Date", "")),
                time=str(r.get("Time", "")),
                status=r.get("Status", ""),
            )
            for r in raw
        ]
    except Exception as exc:
        logger.error("List appointments error", error=str(exc))
        return []
