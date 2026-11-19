"""One-line request logs with a last-line redaction filter.

Never log bodies, query strings, headers, OCR text, prompts, or tokens.
"""

from __future__ import annotations

import logging
import re
import time
from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from app.admin.stats import anonymise_user_id
from app.request_context import accept_request_id, get_request_id, get_user_label, set_request_id, set_user_label

_JWT = re.compile(r"eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+")
_ANT = re.compile(r"sk-ant-[A-Za-z0-9_-]+")
_LONG_NUMBER = re.compile(r"\b\d{12}\b|\b\d{16}\b")

logger = logging.getLogger("esevai.request")


class RedactFilter(logging.Filter):
    """Strip JWTs, Anthropic-looking keys, and 12/16-digit numbers from log text."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = redact_text(str(record.msg))
        if record.args:
            record.args = tuple(
                redact_text(str(arg)) if not isinstance(arg, (int, float)) else arg for arg in record.args
            )
        return True


def redact_text(text: str) -> str:
    cleaned = _JWT.sub("[redacted-jwt]", text)
    cleaned = _ANT.sub("[redacted-key]", cleaned)
    return _LONG_NUMBER.sub("[redacted-number]", cleaned)


def install_logging() -> None:
    root = logging.getLogger()
    if not root.handlers:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    for handler in root.handlers:
        handler.addFilter(RedactFilter())


def log_unhandled(request: Request, exc: Exception) -> None:
    route = _route_template(request)
    logger.error(
        "unhandled error_type=%s request_id=%s route=%s",
        type(exc).__name__,
        get_request_id(),
        route,
    )


def _route_template(request: Request) -> str:
    route = request.scope.get("route")
    path = getattr(route, "path", None)
    if isinstance(path, str) and path:
        return path
    return request.url.path.split("?")[0]


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Assign a request id, time the call, and write one safe summary line."""

    def __init__(self, app: ASGIApp, now: Callable[[], float] | None = None) -> None:
        super().__init__(app)
        self._now = now or time.perf_counter

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = accept_request_id(request.headers.get("x-request-id"))
        set_request_id(request_id)
        set_user_label("-")
        started = self._now()
        try:
            response = await call_next(request)
        except Exception:
            duration = int((self._now() - started) * 1000)
            logger.info(
                "method=%s route=%s status=%s ms=%s request_id=%s user=%s",
                request.method,
                _route_template(request),
                500,
                duration,
                request_id,
                get_user_label(),
            )
            raise
        duration = int((self._now() - started) * 1000)
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "method=%s route=%s status=%s ms=%s request_id=%s user=%s",
            request.method,
            _route_template(request),
            response.status_code,
            duration,
            request_id,
            get_user_label(),
        )
        return response


def remember_user(user_id: str) -> None:
    """Store the anonymised label after authentication succeeds."""
    set_user_label(anonymise_user_id(user_id))
