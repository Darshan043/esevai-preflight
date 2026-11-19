"""Tiny in-memory sliding-window limiter.

Counters live in this process and reset when the server restarts.
"""

from __future__ import annotations

from collections import defaultdict, deque
from time import monotonic

from fastapi import Depends, HTTPException, Request

from app.auth import CurrentUser, get_current_user, require_admin
from app.config import settings


def prune_and_allow(
    timestamps: list[float],
    now: float,
    limit: int,
    window_seconds: float,
) -> tuple[list[float], bool, int]:
    """Drop old hits and decide if one more is allowed. Pure and easy to test."""
    cutoff = now - window_seconds
    kept = [stamp for stamp in timestamps if stamp > cutoff]
    if limit <= 0:
        return kept, False, int(max(1, window_seconds))
    if len(kept) >= limit:
        oldest = kept[0]
        retry = int(max(1, window_seconds - (now - oldest)))
        return kept, False, retry
    kept.append(now)
    return kept, True, 0


class SlidingWindow:
    """One deque of timestamps per key. Not shared across server processes."""

    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def hit(self, key: str, limit: int, window_seconds: float, now: float | None = None) -> tuple[bool, int]:
        current = monotonic() if now is None else now
        bucket = self._hits[key]
        kept, allowed, retry = prune_and_allow(list(bucket), current, limit, window_seconds)
        bucket.clear()
        bucket.extend(kept)
        return allowed, retry

    def reset(self) -> None:
        self._hits.clear()


limiter = SlidingWindow()


def _raise_limited(retry: int) -> None:
    raise HTTPException(
        status_code=429,
        detail="Too many requests. Please wait a minute and try again.",
        headers={"Retry-After": str(retry)},
    )


def limit_user(bucket: str, setting_name: str, window_seconds: int = 3600):
    """FastAPI dependency: authenticated caller, then the named bucket."""

    def dependency(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        limit = int(getattr(settings, setting_name))
        allowed, retry = limiter.hit(f"{bucket}:{user.user_id}", limit, window_seconds)
        if not allowed:
            _raise_limited(retry)
        return user

    return dependency


def client_ip(request: Request) -> str:
    """Use X-Forwarded-For only behind a trusted proxy in production."""
    if str(settings.ENVIRONMENT).strip().lower() == "production":
        forwarded = request.headers.get("x-forwarded-for") or ""
        first = forwarded.split(",")[0].strip()
        if first:
            return first
    return request.client.host if request.client else "unknown"


def limit_ready_ip(request: Request) -> None:
    limit = int(settings.RATE_LIMIT_READY_PER_MINUTE)
    allowed, retry = limiter.hit(f"ready:{client_ip(request)}", limit, 60)
    if not allowed:
        _raise_limited(retry)


def require_admin_write(user: CurrentUser = Depends(require_admin)) -> CurrentUser:
    allowed, retry = limiter.hit(
        f"admin_writes:{user.user_id}",
        int(settings.RATE_LIMIT_ADMIN_WRITES_PER_HOUR),
        3600,
    )
    if not allowed:
        _raise_limited(retry)
    return user


require_upload_user = limit_user("uploads", "RATE_LIMIT_UPLOADS_PER_HOUR")
require_process_user = limit_user("process", "RATE_LIMIT_PROCESS_PER_HOUR")
require_validate_report_user = limit_user("validate_report", "RATE_LIMIT_VALIDATE_REPORT_PER_HOUR")
