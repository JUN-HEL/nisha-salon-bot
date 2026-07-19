"""Customer Tool — read and write customer profiles in SQLite + Sheets."""
from datetime import datetime
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.db_models import Customer
from app.sheets.client import get_sheets_client
from app.database.session import get_session_factory
from app.utils.logger import logger


GET_CUSTOMER_DECLARATION = {
    "name": "get_customer_profile",
    "description": (
        "Retrieve a customer's profile, preferences, favourite service, "
        "preferred stylist, and visit history from the database."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "phone": {"type": "string", "description": "Customer phone number with country code."},
        },
        "required": ["phone"],
    },
}

SAVE_CUSTOMER_DECLARATION = {
    "name": "save_customer_profile",
    "description": (
        "Save or update a customer's name, preferences, favourite service, "
        "or preferred stylist. Call this after learning something new about the customer."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "phone":             {"type": "string",  "description": "Customer phone number."},
            "name":              {"type": "string",  "description": "Customer name."},
            "preferred_stylist": {"type": "string",  "description": "Their preferred stylist."},
            "favorite_service":  {"type": "string",  "description": "Their favourite service."},
            "preferences":       {"type": "string",  "description": "Free-text notes or preferences."},
            "increment_visits":  {"type": "boolean", "description": "Set to true after a completed appointment."},
        },
        "required": ["phone"],
    },
}


async def get_customer_profile(phone: str) -> dict[str, Any]:
    logger.info("Customer profile lookup", phone=phone)
    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(select(Customer).where(Customer.phone == phone))
        customer = result.scalar_one_or_none()
        if not customer:
            return {"found": False, "phone": phone}
        return {
            "found": True,
            "phone": customer.phone,
            "name": customer.name,
            "preferences": customer.preferences,
            "favorite_service": customer.favorite_service,
            "preferred_stylist": customer.preferred_stylist,
            "visit_count": customer.visit_count,
            "last_visit": str(customer.last_visit) if customer.last_visit else None,
        }


async def save_customer_profile(
    phone: str,
    name: Optional[str] = None,
    preferred_stylist: Optional[str] = None,
    favorite_service: Optional[str] = None,
    preferences: Optional[str] = None,
    increment_visits: bool = False,
) -> dict[str, Any]:
    logger.info("Saving customer profile", phone=phone, name=name)
    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(select(Customer).where(Customer.phone == phone))
        customer = result.scalar_one_or_none()

        if not customer:
            customer = Customer(phone=phone)
            session.add(customer)

        if name:
            customer.name = name
        if preferred_stylist:
            customer.preferred_stylist = preferred_stylist
        if favorite_service:
            customer.favorite_service = favorite_service
        if preferences:
            customer.preferences = preferences
        if increment_visits:
            customer.visit_count = (customer.visit_count or 0) + 1
            customer.last_visit = datetime.utcnow()

        await session.commit()
        await session.refresh(customer)

    # Mirror to Google Sheets asynchronously (best-effort)
    try:
        get_sheets_client().upsert_customer({
            "phone": phone,
            "name": customer.name,
            "preferred_stylist": customer.preferred_stylist,
            "favorite_service": customer.favorite_service,
            "visit_count": customer.visit_count,
            "last_visit": str(customer.last_visit) if customer.last_visit else "",
            "notes": customer.preferences,
        })
    except Exception as exc:
        logger.warning("Sheets customer sync failed (non-fatal)", error=str(exc))

    return {
        "success": True,
        "phone": phone,
        "name": customer.name,
        "visit_count": customer.visit_count,
    }
