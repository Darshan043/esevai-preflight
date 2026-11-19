"""One JSON error shape for every backend failure.

The body never includes stack traces, tokens, OCR text, or exception messages
from libraries. HTTPException.detail is already a citizen-facing sentence.
"""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.request_context import get_request_id

_CODES = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    409: "CONFLICT",
    413: "PAYLOAD_TOO_LARGE",
    415: "UNSUPPORTED_MEDIA_TYPE",
    422: "VALIDATION_ERROR",
    429: "RATE_LIMITED",
    500: "INTERNAL_ERROR",
    502: "UPSTREAM_ERROR",
    503: "UNAVAILABLE",
}

GENERIC_500 = "Something went wrong on our side. Please try again."


def code_for_status(status: int) -> str:
    return _CODES.get(status, "ERROR")


def error_envelope(
    status: int,
    message: str,
    *,
    fields: list[dict[str, str]] | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the public error object. extra holds non-secret fields such as upload status."""
    payload: dict[str, Any] = {
        "error": {
            "code": code_for_status(status),
            "message": message,
            "request_id": get_request_id(),
        }
    }
    if fields:
        payload["error"]["fields"] = fields
    if extra:
        payload.update(extra)
    return payload


def error_response(
    status: int,
    message: str,
    *,
    fields: list[dict[str, str]] | None = None,
    extra: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    hdrs = {"X-Request-ID": get_request_id()}
    if headers:
        hdrs.update(headers)
    return JSONResponse(
        status_code=status,
        content=error_envelope(status, message, fields=fields, extra=extra),
        headers=hdrs,
    )


def _admin_fields(detail: object) -> list[dict[str, str]] | None:
    if not isinstance(detail, list) or not detail:
        return None
    fields: list[dict[str, str]] = []
    for item in detail:
        if not isinstance(item, dict) or "field" not in item or "message" not in item:
            return None
        fields.append({"field": str(item["field"]), "message": str(item["message"])})
    return fields


def _detail_text(detail: object, status: int) -> str:
    if isinstance(detail, str) and detail.strip():
        if status == 404 and detail.strip().lower() in {"not found", "not found."}:
            return "This page was not found."
        return detail
    if isinstance(detail, list) and detail:
        return "Please check the highlighted fields and try again."
    if status == 404:
        return "This page was not found."
    return "This request could not be completed."


def _validation_fields(exc: RequestValidationError) -> list[dict[str, str]]:
    fields: list[dict[str, str]] = []
    for item in exc.errors():
        loc = item.get("loc") or ()
        parts = [str(part) for part in loc if part not in {"body", "query", "path", "header"}]
        name = ".".join(parts) if parts else "body"
        fields.append({"field": name, "message": "This value is not valid."})
    return fields


async def http_exception_handler(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
    headers = dict(exc.headers) if exc.headers else {}
    fields = _admin_fields(exc.detail)
    message = _detail_text(exc.detail, exc.status_code)
    return error_response(exc.status_code, message, fields=fields, headers=headers)


async def validation_exception_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    return error_response(
        422,
        "Please check the highlighted fields and try again.",
        fields=_validation_fields(exc),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    # Re-raise HTTP errors so the dedicated handler can format them.
    if isinstance(exc, (HTTPException, StarletteHTTPException)):
        raise exc
    from app.logging_safe import log_unhandled

    log_unhandled(request, exc)
    return error_response(500, GENERIC_500)
