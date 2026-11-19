"""Reject oversized bodies before FastAPI reads them."""

from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.config import settings
from app.errors import error_response

JSON_CAP = 1 * 1024 * 1024


def upload_cap_bytes() -> int:
    return (max(1, int(settings.MAX_UPLOAD_MB)) + 1) * 1024 * 1024


def is_upload_path(path: str) -> bool:
    return "/documents/" in path and path.startswith("/applications/")


class BodySizeMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        raw = request.headers.get("content-length")
        if raw and raw.isdigit():
            size = int(raw)
            if is_upload_path(request.url.path) and request.method == "POST" and size > upload_cap_bytes():
                return error_response(413, "That file is too large.")
            if request.method in {"POST", "PUT", "PATCH"} and not is_upload_path(request.url.path) and size > JSON_CAP:
                return error_response(413, "That request is too large.")
        return await call_next(request)
