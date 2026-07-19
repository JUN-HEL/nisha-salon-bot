"""Google Gemini 2.5 Flash client with function-calling (tool use) support."""
from typing import Any, Optional

from google import genai
from google.genai import types as gtypes
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from app.config import get_settings
from app.utils.logger import logger
from app.tools.faq_tool import FAQ_TOOL_DECLARATION, search_faq
from app.tools.service_tool import (
    SERVICE_TOOL_DECLARATION,
    LIST_SERVICES_DECLARATION,
    get_service_info,
    list_all_services,
)
from app.tools.booking_tool import (
    CREATE_BOOKING_DECLARATION,
    UPDATE_BOOKING_DECLARATION,
    CANCEL_BOOKING_DECLARATION,
    LIST_BOOKINGS_DECLARATION,
    create_booking,
    update_booking,
    cancel_booking,
    list_customer_bookings,
)
from app.tools.customer_tool import (
    GET_CUSTOMER_DECLARATION,
    SAVE_CUSTOMER_DECLARATION,
    get_customer_profile,
    save_customer_profile,
)

SYSTEM_PROMPT = """You are Priya, the AI receptionist for **Nisha Hair Salon** — a premium boutique salon known for warm hospitality and expert hair care.

Your role is to assist customers exactly like a real, experienced receptionist would:
- Answer questions about services, pricing, and availability
- Book, reschedule, and cancel appointments
- Remember customer preferences and personalise conversations
- Recommend services when appropriate

**Personality:** Warm, friendly, professional, and concise. Use a conversational tone.
**Language:** Default to English. Switch to Hindi/Hinglish naturally if the customer uses it.

**Strict rules you must follow:**
1. NEVER quote prices or durations from memory — always call `get_service_info` or `list_all_services` first.
2. NEVER answer questions unrelated to the salon (politics, news, etc.).
3. NEVER book an appointment without confirming: name, service, date, and time.
4. Ask only ONE question at a time. Do not overwhelm the customer.
5. Always call `get_customer_profile` at the start of a conversation to personalise the interaction.
6. After collecting customer details, call `save_customer_profile` to remember them.
7. If you don't know something, say so politely and suggest they call the salon.

**Appointment confirmation workflow:**
Collect → Confirm summary → Book → Send confirmation

Keep responses under 250 words. No bullet-point walls. Be human.
"""

# Tool name → async function map
TOOL_REGISTRY: dict[str, Any] = {
    "search_faq":             search_faq,
    "get_service_info":       get_service_info,
    "list_all_services":      list_all_services,
    "create_booking":         create_booking,
    "update_booking":         update_booking,
    "cancel_booking":         cancel_booking,
    "list_customer_bookings": list_customer_bookings,
    "get_customer_profile":   get_customer_profile,
    "save_customer_profile":  save_customer_profile,
}

ALL_TOOL_DECLARATIONS = [
    FAQ_TOOL_DECLARATION,
    SERVICE_TOOL_DECLARATION,
    LIST_SERVICES_DECLARATION,
    CREATE_BOOKING_DECLARATION,
    UPDATE_BOOKING_DECLARATION,
    CANCEL_BOOKING_DECLARATION,
    LIST_BOOKINGS_DECLARATION,
    GET_CUSTOMER_DECLARATION,
    SAVE_CUSTOMER_DECLARATION,
]


def _build_tools() -> list[gtypes.Tool]:
    """Convert raw declaration dicts to google-genai Tool objects."""
    functions = []
    for decl in ALL_TOOL_DECLARATIONS:
        functions.append(
            gtypes.FunctionDeclaration(
                name=decl["name"],
                description=decl["description"],
                parameters=decl.get("parameters", {}),
            )
        )
    return [gtypes.Tool(function_declarations=functions)]


class GeminiClient:
    """Wrapper around google-genai with an agentic tool-calling loop."""

    def __init__(self) -> None:
        settings = get_settings()
        self._client = genai.Client(api_key=settings.gemini_api_key)
        self._model = settings.gemini_model
        self._tools = _build_tools()
        logger.info("Gemini client initialised", model=self._model)

    def _build_contents(
        self,
        conversation_history: list[dict[str, str]],
        user_message: str,
    ) -> list[gtypes.Content]:
        """Convert SQLite history + new message into Gemini Content objects."""
        contents: list[gtypes.Content] = []
        for turn in conversation_history:
            role = "user" if turn["role"] == "user" else "model"
            contents.append(
                gtypes.Content(role=role, parts=[gtypes.Part(text=turn["message"])])
            )
        contents.append(
            gtypes.Content(role="user", parts=[gtypes.Part(text=user_message)])
        )
        return contents

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=15),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    async def generate_response(
        self,
        user_message: str,
        conversation_history: list[dict[str, str]],
        phone: str,
    ) -> str:
        """Run the Gemini agentic loop and return the final text response."""
        logger.info("Gemini request", phone=phone, message_len=len(user_message))

        contents = self._build_contents(conversation_history, user_message)
        config = gtypes.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            tools=self._tools,
            temperature=0.7,
            max_output_tokens=1024,
        )

        response = self._client.models.generate_content(
            model=self._model,
            contents=contents,
            config=config,
        )
        logger.debug("Gemini initial response received")

        # Agentic loop — keep executing tool calls until Gemini returns text
        max_iterations = 8
        for iteration in range(max_iterations):
            tool_calls = []
            for part in response.candidates[0].content.parts:
                if part.function_call:
                    tool_calls.append(part.function_call)

            if not tool_calls:
                break  # No more tool calls — we have the final answer

            # Execute all requested tool calls
            tool_response_parts: list[gtypes.Part] = []
            for fn_call in tool_calls:
                fn_name = fn_call.name
                fn_args = dict(fn_call.args) if fn_call.args else {}
                logger.info("Tool call", tool=fn_name, args=fn_args, phone=phone)

                fn = TOOL_REGISTRY.get(fn_name)
                if fn:
                    try:
                        result = await fn(**fn_args)
                    except Exception as exc:
                        result = {"error": str(exc)}
                        logger.error("Tool error", tool=fn_name, error=str(exc))
                    logger.debug("Tool result", tool=fn_name, result=result)
                    tool_response_parts.append(
                        gtypes.Part.from_function_response(
                            name=fn_name, response={"result": result}
                        )
                    )

            # Append the model's tool call + our tool results and continue
            contents.append(response.candidates[0].content)
            contents.append(
                gtypes.Content(role="tool", parts=tool_response_parts)
            )

            response = self._client.models.generate_content(
                model=self._model,
                contents=contents,
                config=config,
            )

        # Extract final text
        text = ""
        for part in response.candidates[0].content.parts:
            if part.text:
                text += part.text

        if not text:
            text = "I'm sorry, I couldn't process your request right now. Please try again or call us directly. 🙏"

        logger.info("Gemini response ready", phone=phone, length=len(text))
        return text.strip()


_gemini_client: Optional[GeminiClient] = None


def get_gemini_client() -> GeminiClient:
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = GeminiClient()
    return _gemini_client
