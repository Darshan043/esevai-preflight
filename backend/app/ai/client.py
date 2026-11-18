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
            http_status = getattr(exc, "code", None)
            if not isinstance(http_status, int):
                http_status = getattr(exc, "status_code", None)
            logger.warning(
                "gemini request failed model=%s category=%s http_status=%s ms=%s attempt=%s",
                model,
                category,
                http_status if isinstance(http_status, int) else "-",
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


# A retry delay at or below this is a short wait. Longer delays are not retried here.
_SHORT_RETRY_SECONDS = 120
_RATE_MARKERS = ("perminute", "persecond", "requestsperminute")
_QUOTA_MARKERS = ("perday", "permonth", "billing")


def _classify(exc: Exception) -> tuple[str, bool]:
    """Return a short category and whether one retry is allowed."""
    name = type(exc).__name__.lower()
    status = getattr(exc, "code", None) or getattr(exc, "status_code", None)
    # Do not inspect the provider message. It can be long and is not logged.
    # Structured status, reason, quota ids, and retry delays are enough.
    code_text = str(getattr(exc, "status", "") or "").lower()
    if "timeout" in name or "deadline" in name:
        return "timeout", False
    if status in {401, 403} or "unauth" in name or "permission" in name:
        return "invalid key", False
    if status == 404 or "notfound" in name or "not_found" in code_text:
        return "model not found", False
    limit = _provider_limit(getattr(exc, "details", None))
    if limit == "quota":
        return "no credit or quota", False
    if limit == "rate" and status == 429:
        return "rate limited", True
    if "resource_exhausted" in code_text or "quota" in name:
        return "no credit or quota", False
    if status == 429 or "rate" in name:
        return "rate limited", True
    if status in {500, 503} or "unavailable" in name or "overloaded" in name:
        return "network", True
    if "connect" in name or "network" in name or "transport" in name:
        return "network", True
    return "network", False


def _provider_limit(payload: object) -> str | None:
    """Tell a short rate limit from exhausted quota using structured details only."""
    saw_rate = False
    saw_quota = False
    for entry in _detail_entries(payload):
        reason = str(entry.get("reason") or "").upper()
        if reason == "RATE_LIMIT_EXCEEDED":
            saw_rate = True
        elif reason in {"QUOTA_EXCEEDED", "BILLING_DISABLED", "BILLING_NOT_ACTIVE"}:
            saw_quota = True
        delay = _retry_seconds(entry.get("retryDelay"))
        if delay is not None:
            if delay <= _SHORT_RETRY_SECONDS:
                saw_rate = True
            else:
                saw_quota = True
        violations = entry.get("violations")
        if not isinstance(violations, list):
            continue
        for violation in violations:
            if not isinstance(violation, dict):
                continue
            label = f"{violation.get('quotaId') or ''} {violation.get('quotaMetric') or ''}"
            folded = label.lower().replace("-", "").replace("_", "")
            if any(marker in folded for marker in _QUOTA_MARKERS):
                saw_quota = True
            elif any(marker in folded for marker in _RATE_MARKERS):
                saw_rate = True
    if saw_quota:
        return "quota"
    if saw_rate:
        return "rate"
    return None


def _detail_entries(payload: object) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    error = payload.get("error")
    details = error.get("details") if isinstance(error, dict) else None
    if not isinstance(details, list):
        details = payload.get("details")
    if not isinstance(details, list):
        return []
    return [entry for entry in details if isinstance(entry, dict)]


def _retry_seconds(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value) if value >= 0 else None
    if isinstance(value, dict):
        return _retry_seconds(value.get("seconds"))
    if not isinstance(value, str):
        return None
    text = value.strip().lower()
    if not text.endswith("s"):
        return None
    number = text[:-1]
    if number.count(".") > 1 or not number.replace(".", "", 1).isdigit():
        return None
    return float(number)
