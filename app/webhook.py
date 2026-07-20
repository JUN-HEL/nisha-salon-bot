
"""WhatsApp webhook routes — verification and inbound message processing."""

from fastapi import APIRouter, Query, HTTPException, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import get_settings
from app.database.session import get_db
from app.models.db_models import ConversationMemory
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

    logger.info(
        "Webhook verification request",
        mode=hub_mode
    )

    if (
        hub_mode == "subscribe"
        and hub_verify_token == settings.whatsapp_verify_token
    ):
        logger.info("Webhook verified successfully")
        return hub_challenge or ""

    logger.warning(
        "Webhook verification failed"
    )

    raise HTTPException(
        status_code=403,
        detail="Invalid verify token"
    )


# ─── POST /webhook — Incoming WhatsApp messages ────────────────────────────────

@router.post("/webhook")
async def receive_message(
    payload: WhatsAppWebhookPayload,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:

    """
    Receive WhatsApp messages, generate Gemini response,
    store conversation, and send reply.
    """

    for entry in payload.entry or []:

        for change in entry.changes or []:

            value = change.value

            if not value or not value.messages:
                continue


            for message in value.messages:

                # Ignore unsupported messages
                if (
                    message.type != "text"
                    or not message.text
                    or not message.from_
                ):
                    logger.debug(
                        "Non-text message ignored"
                    )
                    continue


                phone = message.from_
                user_text = message.text.body.strip()
                inbound_msg_id = message.id


                logger.info(
                    "Inbound WhatsApp message",
                    phone=phone,
                    text=user_text[:80],
                )


                # Mark message as read
                try:
                    await get_whatsapp_client().mark_as_read(
                        inbound_msg_id
                    )

                except Exception as exc:
                    logger.warning(
                        "Failed marking message read",
                        error=str(exc)
                    )


                # Save user message
                db.add(
                    ConversationMemory(
                        phone=phone,
                        role="user",
                        message=user_text,
                    )
                )

                await db.commit()


                # Load previous conversation
                settings = get_settings()

                history_result = await db.execute(
                    select(ConversationMemory)
                    .where(
                        ConversationMemory.phone == phone
                    )
                    .order_by(
                        ConversationMemory.timestamp.asc()
                    )
                    .limit(
                        settings.max_conversation_history
                    )
                )


                history = [
                    {
                        "role": item.role,
                        "message": item.message,
                    }
                    for item in history_result.scalars().all()
                ]


                # Generate Gemini response
                try:

                    ai_response = await get_gemini_client().generate_response(
                        user_message=user_text,
                        conversation_history=history[:-1],
                        phone=phone,
                    )


                except Exception as exc:

                    logger.error(
                        "Gemini generation failed",
                        phone=phone,
                        error=str(exc),
                    )

                    ai_response = (
                        "Sorry, I am having trouble right now. "
                        "Please try again shortly. 🙏"
                    )


                # Save AI response
                db.add(
                    ConversationMemory(
                        phone=phone,
                        role="model",
                        message=ai_response,
                    )
                )

                await db.commit()


                # Send WhatsApp reply
                try:

                    await get_whatsapp_client().send_text_message(
                        phone,
                        ai_response
                    )

                except Exception as exc:

                    logger.error(
                        "WhatsApp reply failed",
                        phone=phone,
                        error=str(exc),
                    )


    return {
        "status": "ok"
    }
