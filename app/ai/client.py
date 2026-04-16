import logging

import anthropic
from decouple import config

from app.ai.system_prompt import get_system_prompt

logger = logging.getLogger(__name__)

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 1024

# The anthropic SDK retries idempotent failures (connection errors, 408, 429,
# 5xx) automatically up to MAX_RETRIES. We use its built-in behaviour rather
# than wrapping our own loop.
MAX_RETRIES = 3
REQUEST_TIMEOUT_SECONDS = 30.0

ERROR_MESSAGES = {
    "fr": "Je rencontre un problème technique. Veuillez réessayer dans un instant.",
    "en": "I'm having a technical issue. Please try again shortly.",
    "es": "Tengo un problema técnico. Por favor, inténtelo de nuevo en un momento.",
    "pt": "Estou com um problema técnico. Por favor, tente novamente em breve.",
}


def _error_message(language: str) -> str:
    return ERROR_MESSAGES.get(language, ERROR_MESSAGES["fr"])


def get_ai_response(history: list[dict], language: str) -> str:
    """Call Claude API with conversation history and return the response text."""
    try:
        client = anthropic.Anthropic(
            api_key=config("ANTHROPIC_API_KEY"),
            max_retries=MAX_RETRIES,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=get_system_prompt(language),
            messages=history,
        )
        return response.content[0].text
    except anthropic.APIStatusError as exc:
        logger.error(
            "Claude API returned status %s: %s", exc.status_code, exc.message
        )
        return _error_message(language)
    except anthropic.APIConnectionError:
        logger.exception("Claude API connection failed after retries")
        return _error_message(language)
    except Exception:
        logger.exception("Unexpected error calling Claude API")
        return _error_message(language)
