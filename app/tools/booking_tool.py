"""Booking Tool — create, update, cancel, and list appointments."""
from datetime import datetime
from typing import Any, Optional

from app.sheets.client import get_sheets_client
from app.utils.logger import logger


CREATE_BOOKING_DECLARATION = {
    "name": "create_booking",
    "description": (
        "Create a new salon appointment after confirming all details with the customer. "
        "Requires name, phone, service, date, and time. Stylist is optional."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "name":    {"type": "string", "description": "Customer's full name."},
            "phone":   {"type": "string", "description": "Customer phone number with country code."},
            "service": {"type": "string", "description": "Service to book (must match available services)."},
            "date":    {"type": "string", "description": "Appointment date in DD-MM-YYYY format."},
            "time":    {"type": "string", "description": "Appointment time in HH:MM format (24h or AM/PM)."},
            "stylist": {"type": "string", "description": "Preferred stylist name (optional)."},
        },
        "required": ["name", "phone", "service", "date", "time"],
    },
}

UPDATE_BOOKING_DECLARATION = {
    "name": "update_booking",
    "description": "Reschedule an existing appointment by changing its date or time.",
    "parameters": {
        "type": "object",
        "properties": {
            "phone":    {"type": "string", "description": "Customer phone number."},
            "old_date": {"type": "string", "description": "Current appointment date in DD-MM-YYYY."},
            "new_date": {"type": "string", "description": "New appointment date in DD-MM-YYYY."},
            "new_time": {"type": "string", "description": "New appointment time."},
        },
        "required": ["phone", "old_date", "new_date", "new_time"],
    },
}

CANCEL_BOOKING_DECLARATION = {
    "name": "cancel_booking",
    "description": "Cancel an existing appointment.",
    "parameters": {
        "type": "object",
        "properties": {
            "phone": {"type": "string", "description": "Customer phone number."},
            "date":  {"type": "string", "description": "Appointment date to cancel in DD-MM-YYYY."},
        },
        "required": ["phone", "date"],
    },
}

LIST_BOOKINGS_DECLARATION = {
    "name": "list_customer_bookings",
    "description": "Retrieve all appointments for a customer.",
    "parameters": {
        "type": "object",
        "properties": {
            "phone": {"type": "string", "description": "Customer phone number."},
        },
        "required": ["phone"],
    },
}


async def create_booking(
    name: str,
    phone: str,
    service: str,
    date: str,
    time: str,
    stylist: str = "",
) -> dict[str, Any]:
    logger.info("Creating booking", phone=phone, service=service, date=date)
    try:
        row = {
            "name": name,
            "phone": phone,
            "service": service,
            "stylist": stylist,
            "date": date,
            "time": time,
            "status": "Confirmed",
        }
        get_sheets_client().create_appointment(row)
        return {
            "success": True,
            "message": (
                f"Appointment confirmed!\n"
                f"📅 Date: {date}\n"
                f"⏰ Time: {time}\n"
                f"💇 Service: {service}"
                + (f"\n✂️ Stylist: {stylist}" if stylist else "")
            ),
            "booking": row,
        }
    except Exception as exc:
        logger.error("Create booking error", error=str(exc))
        return {"success": False, "error": str(exc)}


async def update_booking(
    phone: str, old_date: str, new_date: str, new_time: str
) -> dict[str, Any]:
    logger.info("Updating booking", phone=phone, old_date=old_date, new_date=new_date)
    try:
        # Cancel old, but keep the record as Rescheduled
        sheets = get_sheets_client()
        updated = sheets.update_appointment_status(phone, old_date, "Rescheduled")
        if not updated:
            return {"success": False, "message": "Original appointment not found."}

        # Fetch the old appointment to carry forward name/service/stylist
        appts = sheets.get_appointments(phone=phone)
        old = next(
            (a for a in appts if str(a.get("Date", "")) == old_date), {}
        )
        new_row = {
            "name": old.get("Name", ""),
            "phone": phone,
            "service": old.get("Service", ""),
            "stylist": old.get("Stylist", ""),
            "date": new_date,
            "time": new_time,
            "status": "Confirmed",
        }
        sheets.create_appointment(new_row)
        return {
            "success": True,
            "message": (
                f"Your appointment has been rescheduled to {new_date} at {new_time}. "
                f"We look forward to seeing you! 😊"
            ),
        }
    except Exception as exc:
        logger.error("Update booking error", error=str(exc))
        return {"success": False, "error": str(exc)}


async def cancel_booking(phone: str, date: str) -> dict[str, Any]:
    logger.info("Cancelling booking", phone=phone, date=date)
    try:
        ok = get_sheets_client().update_appointment_status(phone, date, "Cancelled")
        if ok:
            return {
                "success": True,
                "message": "Your appointment has been cancelled. We hope to see you again soon! 🙏",
            }
        return {"success": False, "message": "No appointment found for that date."}
    except Exception as exc:
        logger.error("Cancel booking error", error=str(exc))
        return {"success": False, "error": str(exc)}


async def list_customer_bookings(phone: str) -> dict[str, Any]:
    logger.info("Listing bookings", phone=phone)
    try:
        appts = get_sheets_client().get_appointments(phone=phone)
        active = [a for a in appts if a.get("Status", "") not in ("Cancelled",)]
        return {"success": True, "appointments": active, "count": len(active)}
    except Exception as exc:
        logger.error("List bookings error", error=str(exc))
        return {"success": False, "appointments": [], "error": str(exc)}
