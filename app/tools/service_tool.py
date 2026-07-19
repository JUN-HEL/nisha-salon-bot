"""Service Tool — returns pricing, duration, and availability."""
from difflib import SequenceMatcher
from typing import Any

from app.sheets.client import get_sheets_client
from app.utils.logger import logger


SERVICE_TOOL_DECLARATION = {
    "name": "get_service_info",
    "description": (
        "Retrieve details about a specific salon service: price, estimated duration, "
        "stylist availability, and whether the service is currently offered. "
        "Always use this tool before quoting prices or durations."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "service_name": {
                "type": "string",
                "description": "The name of the service the customer is asking about (e.g. 'haircut', 'balayage', 'keratin treatment').",
            }
        },
        "required": ["service_name"],
    },
}

LIST_SERVICES_DECLARATION = {
    "name": "list_all_services",
    "description": (
        "Return the full list of services offered by the salon with prices and durations. "
        "Use this when the customer asks 'what services do you offer' or wants to browse."
    ),
    "parameters": {"type": "object", "properties": {}},
}


def _score(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


async def get_service_info(service_name: str) -> dict[str, Any]:
    logger.info("Service tool called", service=service_name)
    try:
        services = get_sheets_client().get_services()
        if not services:
            return {"found": False, "message": "Service information is unavailable right now."}

        best = max(services, key=lambda s: _score(service_name, s["service"]))
        score = _score(service_name, best["service"])

        if score >= 0.4:
            return {
                "found": True,
                "service": best["service"],
                "price": best["price"],
                "duration": best["duration"],
                "availability": best["availability"],
            }
        return {
            "found": False,
            "message": f"We couldn't find a service matching '{service_name}'. Try asking for our full service list.",
        }
    except Exception as exc:
        logger.error("Service tool error", error=str(exc))
        return {"found": False, "error": str(exc)}


async def list_all_services() -> dict[str, Any]:
    logger.info("List services tool called")
    try:
        services = get_sheets_client().get_services()
        return {"services": services, "count": len(services)}
    except Exception as exc:
        logger.error("List services error", error=str(exc))
        return {"services": [], "error": str(exc)}
