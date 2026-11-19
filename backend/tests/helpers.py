"""Read the citizen-facing sentence from either error envelope."""

from __future__ import annotations

from typing import Any


def api_message(response: Any) -> str:
    body = response.json()
    error = body.get("error") if isinstance(body, dict) else None
    if isinstance(error, dict) and isinstance(error.get("message"), str):
        return error["message"]
    detail = body.get("detail") if isinstance(body, dict) else None
    if isinstance(detail, str):
        return detail
    return ""


def api_error(response: Any) -> dict[str, Any]:
    body = response.json()
    error = body.get("error") if isinstance(body, dict) else None
    return error if isinstance(error, dict) else {}
