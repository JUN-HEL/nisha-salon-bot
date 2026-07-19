"""WhatsApp webhook routes — verification and inbound message processing."""
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Query, HTTPException, Request, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.config import get_settings
from app.database.session import get_db
from app.models.db_models import ConversationMemory, Customer
from app.schemas.pydantic_schemas import WhatsAppWebhookPayload
from app.ai.gemini_client import get_gemini_client
from app.whatsapp.client import get_whatsapp_client
from app.utils.logger import logger

router = APIRouter()


# ─── GET /webhook — Meta verification handshake ────────────────────────────────

@router.get("/webhook", response_class=PlainTextResponse)
async def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
) -> str:
    settings = get_settings()
    logger.info("Webhook verification request", mode=hub_mode)

    if hub_mode == "subscribe" and hub_verify_token == settings.whatsapp_verify_token:
        logger.info("Webhook verified successfully")
        return hub_challenge or ""

    logger.warning("Webhook verification failed", token=hub_verify_token)
    raise HTTPException(status_code=403, detail="Forbidden — invalid verify token")


# ─── POST /webhook — Inbound messages ─────────────────────────────────────────

@router.post("/webhook")
async def receive_message(
    payload: WhatsAppWebhookPayload,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Process every inbound WhatsApp message through the Gemini agentic loop."""
    for entry in payload.entry:
        for change in entry.changes:
            value = change.value
            if not value.messages:
                continue

            for message in value.messages:
                if message.type != "text" or not message.text:
                    logger.debug("Non-text message ignored", type=message.type)
                    continue

                phone = message.from_
                user_text = message.text.body.strip()
                inbound_msg_id = message.id

                logger.info("Inbound message", phone=phone, text=user_text[:80])

                # Mark as read immediately
                try:
                    await get_whatsapp_client().mark_as_read(inbound_msg_id)
                except Exception:
                    pass

                # 1. Persist user message
                db.add(ConversationMemory(phone=phone, role="user", message=user_text))
                await db.commit()

                # 2. Load conversation history (last N turns)
                settings = get_settings()
                history_result = await db.execute(
                    select(ConversationMemory)
                    .where(ConversationMemory.phone == phone)
                    .order_by(ConversationMemory.timestamp.asc())
                    .limit(settings.max_conversation_history)
                )
                history = [
                    {"role": h.role, "message": h.message}
                    for h in history_result.scalars().all()
                ]

                # 3. Run Gemini agentic loop
                try:
                    ai_response = await get_gemini_client().generate_response(
                        user_message=user_text,
                        conversation_history=history[:-1],  # exclude the just-added message
                        phone=phone,
                    )
                except Exception as exc:
                    logger.error("Gemini error", phone=phone, error=str(exc))
                    ai_response = (
                        "I'm sorry, I'm having a little trouble right now. "
                        "Please try again in a moment or call us directly. 🙏"
                    )

                # 4. Persist AI response
                db.add(ConversationMemory(phone=phone, role="model", message=ai_response))
                await db.commit()

                # 5. Send reply
                try:
                    await get_whatsapp_client().send_text_message(phone, ai_response)
                except Exception as exc:
                    logger.error("WhatsApp send error", phone=phone, error=str(exc))

    return {"status": "ok"}
