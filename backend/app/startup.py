"""Refuse to start in production when required settings are missing or unsafe.

Messages name variable names only. Values are never included.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_LOCAL_MARKERS = ("localhost", "127.0.0.1", "0.0.0.0", "[::1]")


def parse_origins(raw: str) -> list[str]:
    return [part.strip() for part in raw.split(",") if part.strip()]


def origin_is_unsafe(origin: str) -> bool:
    lowered = origin.lower()
    if origin == "*" or "*" in origin:
        return True
    if any(marker in lowered for marker in _LOCAL_MARKERS):
        return True
    return not lowered.startswith("https://")


def missing_required(settings: Any) -> list[str]:
    """Setting names that are empty. Localhost origins are allowed in development."""
    names: list[str] = []
    if not str(getattr(settings, "SUPABASE_URL", "") or "").strip():
        names.append("SUPABASE_URL")
    if not str(getattr(settings, "SUPABASE_SERVICE_ROLE_KEY", "") or "").strip():
        names.append("SUPABASE_SERVICE_ROLE_KEY")
    if not parse_origins(str(getattr(settings, "ALLOWED_ORIGINS", "") or "")):
        names.append("ALLOWED_ORIGINS")
    if bool(getattr(settings, "AI_ENABLED", False)):
        # Live AI in this project is Gemini. Anthropic names stay in .env.example only.
        if not str(getattr(settings, "GEMINI_API_KEY", "") or "").strip():
            names.append("GEMINI_API_KEY")
        if not str(getattr(settings, "GEMINI_MODEL", "") or "").strip():
            names.append("GEMINI_MODEL")
    return names


def production_problems(settings: Any) -> list[str]:
    """Return the names of settings that would be unsafe in production."""
    names = missing_required(settings)
    origins = parse_origins(str(getattr(settings, "ALLOWED_ORIGINS", "") or ""))
    if origins and any(origin_is_unsafe(origin) for origin in origins) and "ALLOWED_ORIGINS" not in names:
        names.append("ALLOWED_ORIGINS")
    return names


def docs_enabled(settings: Any) -> bool:
    raw = str(getattr(settings, "ENABLE_DOCS", "") or "").strip().lower()
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    return str(getattr(settings, "ENVIRONMENT", "development") or "").strip().lower() != "production"


def validate_settings(settings: Any) -> None:
    environment = str(getattr(settings, "ENVIRONMENT", "development") or "").strip().lower()
    if environment not in {"development", "production"}:
        raise RuntimeError("ENVIRONMENT must be development or production.")
    if environment == "production":
        problems = production_problems(settings)
        if problems:
            joined = ", ".join(problems)
            raise RuntimeError(f"Cannot start in production. Missing or unsafe: {joined}.")
        return
    incomplete = missing_required(settings)
    if incomplete:
        logger.warning("development settings incomplete: %s", ", ".join(incomplete))
