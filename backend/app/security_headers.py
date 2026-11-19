"""Security headers on every backend response."""

from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.config import settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        if str(settings.ENVIRONMENT).strip().lower() == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        content_type = response.headers.get("content-type", "")
        authorization = request.headers.get("authorization")
        if authorization and "application/json" in content_type:
            response.headers["Cache-Control"] = "no-store"
        return response
