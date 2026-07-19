"""WhatsApp Cloud API client — send messages and mark as read."""
from typing import Any, Optional
import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from app.config import get_settings
from app.utils.logger import logger


class WhatsAppClient:
    """Async client for the WhatsApp Business Cloud API."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._base_url = (
            f"{self._settings.whatsapp_api_base_url}"
            f"/{self._settings.whatsapp_phone_number_id}"
        )
        self._headers = {
            "Authorization": f"Bearer {self._settings.whatsapp_access_token}",
            "Content-Type": "application/json",
        }

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type(httpx.HTTPError),
        reraise=True,
    )
    async def send_text_message(self, to: str, text: str) -> Optional[str]:
        """Send a text message. Returns message_id on success."""
        payload: dict[str, Any] = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "text",
            "text": {"body": text, "preview_url": False},
        }
        logger.info("Sending WhatsApp message", to=to, length=len(text))
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self._base_url}/messages",
                json=payload,
                headers=self._headers,
            )
            data = response.json()
            if response.is_success:
                msg_id = data.get("messages", [{}])[0].get("id")
                logger.info("Message sent", to=to, message_id=msg_id)
                return msg_id
            else:
                logger.error(
                    "WhatsApp API error",
                    status=response.status_code,
                    body=data,
                )
                raise httpx.HTTPStatusError(
                    f"WhatsApp API returned {response.status_code}",
                    request=response.request,
                    response=response,
                )

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        retry=retry_if_exception_type(httpx.HTTPError),
        reraise=True,
    )
    async def mark_as_read(self, message_id: str) -> None:
        """Mark a message as read (shows double blue tick)."""
        payload = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id,
        }
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(
                f"{self._base_url}/messages",
                json=payload,
                headers=self._headers,
            )

    async def send_typing_indicator(self, phone: str) -> None:
        """Show typing indicator (best-effort, no retry)."""
        # WhatsApp doesn't natively expose a typing indicator endpoint;
        # we mark the last inbound message as read which shows
        # the double-tick while the AI is processing.
        pass


_whatsapp_client: Optional[WhatsAppClient] = None


def get_whatsapp_client() -> WhatsAppClient:
    global _whatsapp_client
    if _whatsapp_client is None:
        _whatsapp_client = WhatsAppClient()
    return _whatsapp_client
