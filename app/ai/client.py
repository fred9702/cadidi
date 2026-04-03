import logging

import anthropic
from decouple import config

from app.ai.system_prompt import get_system_prompt

logger = logging.getLogger(__name__)

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 1024

ERROR_MESSAGES = {
    "fr": "Je rencontre un problème technique. Veuillez réessayer dans un instant.",
    "en": "I'm having a technical issue. Please try again shortly.",
}


def get_ai_response(history: list[dict], language: str) -> str:
    """Call Claude API with conversation history and return the response text."""
    try:
        client = anthropic.Anthropic(api_key=config("ANTHROPIC_API_KEY"))
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=get_system_prompt(language),
            messages=history,
        )
        return response.content[0].text
    except Exception:
        logger.exception("Claude API call failed")
        return ERROR_MESSAGES.get(language, ERROR_MESSAGES["fr"])
