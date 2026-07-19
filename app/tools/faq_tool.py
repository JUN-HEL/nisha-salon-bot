"""FAQ Tool — answers salon FAQs from Google Sheets."""
from difflib import SequenceMatcher
from typing import Any

from app.sheets.client import get_sheets_client
from app.utils.logger import logger


# Gemini function declaration
FAQ_TOOL_DECLARATION = {
    "name": "search_faq",
    "description": (
        "Search the salon's FAQ database for an answer to the customer's question. "
        "Use this tool whenever a customer asks a general question about the salon, "
        "policies, hours, location, parking, payment, or any other FAQ topic."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "The customer's question, verbatim or paraphrased.",
            }
        },
        "required": ["question"],
    },
}


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


async def search_faq(question: str) -> dict[str, Any]:
    """Find the best matching FAQ answer for a question."""
    logger.info("FAQ tool called", question=question)
    try:
        faqs = get_sheets_client().get_faqs()
        if not faqs:
            return {"found": False, "answer": "I don't have FAQ data available right now."}

        best_match = max(faqs, key=lambda f: _similarity(question, f["question"]))
        score = _similarity(question, best_match["question"])

        logger.debug("FAQ match", score=score, question=best_match["question"])

        if score >= 0.60:
            return {
                "found": True,
                "matched_question": best_match["question"],
                "answer": best_match["answer"],
                "confidence": round(score, 2),
            }
        return {
            "found": False,
            "answer": (
                "I couldn't find a specific answer to that question. "
                "Please call us or visit the salon for more details."
            ),
        }
    except Exception as exc:
        logger.error("FAQ tool error", error=str(exc))
        return {"found": False, "error": str(exc)}
