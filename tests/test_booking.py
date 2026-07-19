"""Integration-style tests for booking flows."""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime


@pytest.mark.asyncio
async def test_update_booking_reschedules():
    mock_appts = [
        {"Name": "Asha", "Phone": "919876543210", "Service": "Facial", "Stylist": "Nisha",
         "Date": "20-07-2025", "Time": "10:00", "Status": "Confirmed"}
    ]
    with patch("app.tools.booking_tool.get_sheets_client") as mock_client:
        inst = mock_client.return_value
        inst.update_appointment_status.return_value = True
        inst.get_appointments.return_value = mock_appts
        inst.create_appointment.return_value = True

        from app.tools.booking_tool import update_booking
        result = await update_booking(
            phone="919876543210",
            old_date="20-07-2025",
            new_date="22-07-2025",
            new_time="14:00",
        )
        assert result["success"] is True
        assert "rescheduled" in result["message"].lower()


@pytest.mark.asyncio
async def test_list_customer_bookings():
    mock_appts = [
        {"Name": "Asha", "Phone": "919876543210", "Service": "Haircut",
         "Stylist": "", "Date": "25-07-2025", "Time": "11:00", "Status": "Confirmed"}
    ]
    with patch("app.tools.booking_tool.get_sheets_client") as mock_client:
        mock_client.return_value.get_appointments.return_value = mock_appts
        from app.tools.booking_tool import list_customer_bookings
        result = await list_customer_bookings(phone="919876543210")
        assert result["success"] is True
        assert result["count"] == 1
