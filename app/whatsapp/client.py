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

        logger.info(
            f"WhatsApp client initialized: {self._base_url}"
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type(httpx.HTTPError),
        reraise=True,
    )
    async def send_text_message(
        self,
        to: str,
        text: str
    ) -> Optional[str]:
        """Send a text message. Returns message_id on success."""

        payload: dict[str, Any] = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "text",
            "text": {
                "body": text,
                "preview_url": False,
            },
        }

        logger.info(
            f"Sending WhatsApp message to={to}, length={len(text)}"
        )

        async with httpx.AsyncClient(timeout=30) as client:

            response = await client.post(
                f"{self._base_url}/messages",
                json=payload,
                headers=self._headers,
            )

            try:
                data = response.json()
            except Exception:
                data = response.text

            if response.is_success:
                msg_id = (
                    data.get("messages", [{}])[0].get("id")
                    if isinstance(data, dict)
                    else None
                )

                logger.info(
                    f"WhatsApp message sent successfully id={msg_id}"
                )

                return msg_id

            else:
                # IMPORTANT: Shows the real Meta error in Render logs
                logger.error(
                    f"""
                    WhatsApp API FAILED
                    Status: {response.status_code}
                    Response: {data}
                    URL: {self._base_url}/messages
                    """
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
        """Mark a message as read."""

        payload = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id,
        }

        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                f"{self._base_url}/messages",
                json=payload,
                headers=self._headers,
            )

            if not response.is_success:
                logger.warning(
                    f"Failed marking message read: {response.text}"
                )

    async def send_typing_indicator(self, phone: str) -> None:
        """
        WhatsApp does not provide a typing indicator API.
        Marking messages as read gives the user feedback.
        """
        pass


_whatsapp_client: Optional[WhatsAppClient] = None


def get_whatsapp_client() -> WhatsAppClient:
    global _whatsapp_client

    if _whatsapp_client is None:
        _whatsapp_client = WhatsAppClient()

    return _whatsapp_client