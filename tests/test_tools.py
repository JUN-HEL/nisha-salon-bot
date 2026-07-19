"""Unit tests for AI tools."""
import pytest
from unittest.mock import patch, MagicMock


# ─── FAQ Tool ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_faq_tool_found():
    mock_faqs = [
        {"question": "What are your opening hours?", "answer": "9am – 7pm Mon-Sat"},
        {"question": "Do you accept walk-ins?", "answer": "Yes, subject to availability"},
    ]
    with patch("app.tools.faq_tool.get_sheets_client") as mock_client:
        mock_client.return_value.get_faqs.return_value = mock_faqs
        from app.tools.faq_tool import search_faq
        result = await search_faq("What time do you open?")
        assert result["found"] is True
        assert "9am" in result["answer"]


@pytest.mark.asyncio
async def test_faq_tool_not_found():
    mock_faqs = [
        {"question": "What are your opening hours?", "answer": "9am – 7pm Mon-Sat"},
    ]
    with patch("app.tools.faq_tool.get_sheets_client") as mock_client:
        mock_client.return_value.get_faqs.return_value = mock_faqs
        from app.tools.faq_tool import search_faq
        result = await search_faq("cryptocurrency prices today")
        assert result["found"] is False


# ─── Service Tool ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_service_info_found():
    mock_services = [
        {"service": "Haircut", "price": "₹500", "duration": "45 mins", "availability": "All stylists"},
    ]
    with patch("app.tools.service_tool.get_sheets_client") as mock_client:
        mock_client.return_value.get_services.return_value = mock_services
        from app.tools.service_tool import get_service_info
        result = await get_service_info("haircut")
        assert result["found"] is True
        assert result["price"] == "₹500"


@pytest.mark.asyncio
async def test_list_all_services():
    mock_services = [
        {"service": "Haircut", "price": "₹500", "duration": "45 mins", "availability": "All"},
        {"service": "Balayage", "price": "₹3000", "duration": "3 hrs", "availability": "Senior stylist"},
    ]
    with patch("app.tools.service_tool.get_sheets_client") as mock_client:
        mock_client.return_value.get_services.return_value = mock_services
        from app.tools.service_tool import list_all_services
        result = await list_all_services()
        assert result["count"] == 2


# ─── Booking Tool ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_booking_success():
    with patch("app.tools.booking_tool.get_sheets_client") as mock_client:
        mock_client.return_value.create_appointment.return_value = True
        from app.tools.booking_tool import create_booking
        result = await create_booking(
            name="Priya Sharma",
            phone="919876543210",
            service="Haircut",
            date="25-07-2025",
            time="11:00",
            stylist="Nisha",
        )
        assert result["success"] is True
        assert "confirmed" in result["message"].lower()


@pytest.mark.asyncio
async def test_cancel_booking_not_found():
    with patch("app.tools.booking_tool.get_sheets_client") as mock_client:
        mock_client.return_value.update_appointment_status.return_value = False
        from app.tools.booking_tool import cancel_booking
        result = await cancel_booking(phone="919999999999", date="01-01-2099")
        assert result["success"] is False
