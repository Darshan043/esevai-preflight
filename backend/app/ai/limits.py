"""Count AI calls per person for the current UTC day.

The counts live in memory. They reset when the server restarts, which is acceptable here.
"""

from datetime import datetime, timezone

from fastapi import HTTPException

from app.config import settings

# user id -> (utc date, calls already accepted today)
_counts: dict[str, tuple[object, int]] = {}


def reserve_call(user_id: str) -> None:
    """Count one call, or refuse when today's limit is already used."""
    today = datetime.now(timezone.utc).date()
    day, count = _counts.get(user_id, (today, 0))
    if day != today:
        count = 0
    if count >= settings.AI_MAX_CALLS_PER_USER_PER_DAY:
        raise HTTPException(
            status_code=429,
            detail="The daily AI limit has been reached. Please try again tomorrow.",
        )
    _counts[user_id] = (today, count + 1)


def reset_counts() -> None:
    """Clear the counter. Tests use this so one test does not affect the next."""
    _counts.clear()
