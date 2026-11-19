"""Readiness checks used by GET /health/ready. Each check is a short ok/fail string."""

from __future__ import annotations

import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any

from app.config import settings
from app.supabase_client import SupabaseRequestError, count_rows, ping_storage


def tesseract_available() -> bool:
    command = settings.TESSERACT_CMD.strip()
    if command:
        return Path(command).exists() or shutil.which(command) is not None
    return shutil.which("tesseract") is not None


def tamil_ocr_ready() -> str:
    requested = (settings.OCR_LANGS or "").lower()
    if "tam" not in requested.split("+") and "tam" not in requested.split(","):
        return "no"
    try:
        from app.processing import ocr as ocr_mod

        return "yes" if "tam" in ocr_mod._languages() else "no"
    except Exception:
        return "no"


def check_database() -> str:
    try:
        count_rows("profiles", {"select": "id"})
        return "ok"
    except Exception:
        return "fail"


def check_storage() -> str:
    try:
        ping_storage()
        return "ok"
    except (SupabaseRequestError, Exception):
        return "fail"


def check_ocr() -> str:
    return "ok" if tesseract_available() else "fail"


def classify_ready(required: dict[str, str], optional: dict[str, str]) -> tuple[int, str]:
    """200 when required checks pass. 503 when a required check fails."""
    if any(value == "fail" for value in required.values()):
        return 503, "degraded"
    if any(value in {"fail", "no"} for value in optional.values()):
        return 200, "degraded"
    return 200, "ok"


def ready_body(
    *,
    database: Callable[[], str] = check_database,
    storage: Callable[[], str] = check_storage,
    ocr: Callable[[], str] = check_ocr,
    tamil: Callable[[], str] = tamil_ocr_ready,
) -> tuple[int, dict[str, Any]]:
    required = {
        "database": database(),
        "storage": storage(),
        "ocr": ocr(),
    }
    optional = {"tamil_ocr": tamil()}
    http_status, status = classify_ready(required, optional)
    return http_status, {"status": status, "checks": {**required, **optional}}
