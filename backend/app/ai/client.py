"""One Gemini call that must return JSON.

The API key is passed in from settings. Nothing here is written to the log.
"""

import logging
import time
from typing import Any

from google import genai
from google.genai import types

from app.config import settings

logger = logging.getLogger(__name__)

# Short labels we may show or log. Raw SDK messages stay inside this module.
_FRIENDLY = {
    "no key": "AI assistance is unavailable right now. Your standard checks still work.",
    "invalid key": "AI assistance is unavailable right now. Your standard checks still work.",
    "no credit or quota": "AI assistance is unavailable right now. Your standard checks still work.",
    "model not found": "AI assistance is unavailable right now. Your standard checks still work.",
    "timeout": "AI assistance is unavailable right now. Your standard checks still work.",
    "rate limited": "AI assistance is busy right now. Please try again in a little while.",
    "network": "AI assistance is unavailable right now. Your standard checks still work.",
    "off": "AI assistance is turned off.",
}


class AIUnavailableError(Exception):
    """The model could not be used. category is a short label, not the SDK text."""

    def __init__(self, category: str) -> None:
        self.category = category if category in _FRIENDLY else "network"
        super().__init__(_FRIENDLY[self.category])

    @property
    def status_code(self) -> int:
        if self.category == "rate limited":
            return 429
        if self.category == "off":
            return 503
        return 503


def friendly_message(category: str) -> str:
    return _FRIENDLY.get(category, _FRIENDLY["network"])


def build_client() -> genai.Client:
    """Create the official client. Tests replace this so they never call Google."""
    key = settings.GEMINI_API_KEY.strip()
    if not key:
        raise AIUnavailableError("no key")
    timeout_ms = max(1, int(settings.AI_TIMEOUT_SECONDS)) * 1000
    return genai.Client(api_key=key, http_options=types.HttpOptions(timeout=timeout_ms))


def complete_json(system: str, user: str, max_tokens: int | None = None) -> tuple[str, dict[str, int]]:
    """Ask the configured model for one JSON reply. Retries once on a transient error."""
    model = (settings.GEMINI_MODEL or "").strip() or "gemini-3.8-flash"
    if not settings.GEMINI_API_KEY.strip():
        raise AIUnavailableError("no key")
    limit = max_tokens if max_tokens is not None else settings.AI_MAX_OUTPUT_TOKENS
    last_category = "network"
    for attempt in (1, 2):
        started = time.perf_counter()
        try:
            client = build_client()
            response = client.models.generate_content(
                model=model,
                contents=user,
                config=types.GenerateContentConfig(
                    system_instruction=system,
                    max_output_tokens=limit,
                    response_mime_type="application/json",
                ),
            )
            text = getattr(response, "text", None) or ""
            usage = _usage(response)
            logger.info(
                "gemini finished model=%s status=ok ms=%s prompt_tokens=%s output_tokens=%s",
                model,
                int((time.perf_counter() - started) * 1000),
                usage["prompt_tokens"],
                usage["output_tokens"],
            )
            return text, usage
        except AIUnavailableError:
            raise
        except Exception as exc:
            category, transient = _classify(exc)
            last_category = category
            logger.info(
                "gemini finished model=%s status=%s ms=%s attempt=%s",
                model,
                category,
                int((time.perf_counter() - started) * 1000),
                attempt,
            )
            if transient and attempt == 1:
                continue
            raise AIUnavailableError(category) from None
    raise AIUnavailableError(last_category)


def _usage(response: Any) -> dict[str, int]:
    meta = getattr(response, "usage_metadata", None)
    prompt = getattr(meta, "prompt_token_count", None) if meta is not None else None
    output = getattr(meta, "candidates_token_count", None) if meta is not None else None
    return {
        "prompt_tokens": int(prompt or 0),
        "output_tokens": int(output or 0),
    }


def _classify(exc: Exception) -> tuple[str, bool]:
    """Return a short category and whether one retry is allowed."""
    name = type(exc).__name__.lower()
    status = getattr(exc, "code", None) or getattr(exc, "status_code", None)
    text = f"{name} {status or ''}".lower()
    # Do not inspect a long message that might echo a key. Status and type are enough,
    # plus a few stable words Google puts in the exception class or code.
    blob = text
    code_text = str(getattr(exc, "status", "") or "").lower()
    blob = f"{blob} {code_text}"
    if "timeout" in name or "deadline" in name:
        return "timeout", False
    if status in {401, 403} or "unauth" in name or "permission" in name:
        return "invalid key", False
    if status == 404 or "notfound" in name or "not_found" in code_text:
        return "model not found", False
    if "resource_exhausted" in code_text or "quota" in name:
        return "no credit or quota", False
    if status == 429 or "rate" in name:
        return "rate limited", True
    if status in {500, 503} or "unavailable" in name or "overloaded" in name:
        return "network", True
    if "connect" in name or "network" in name or "transport" in name:
        return "network", True
    return "network", False
