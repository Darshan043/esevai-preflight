"""Request id stored for the current call. Middleware sets it once."""

from __future__ import annotations

import re
import uuid
from contextvars import ContextVar

_REQUEST_ID: ContextVar[str] = ContextVar("request_id", default="-")
_USER_LABEL: ContextVar[str] = ContextVar("user_label", default="-")

# Incoming ids may only be short, boring characters. Anything else is replaced.
_SAFE_ID = re.compile(r"^[A-Za-z0-9._-]{8,64}$")


def new_request_id() -> str:
    return uuid.uuid4().hex[:16]


def accept_request_id(raw: str | None) -> str:
    """Use the caller's id only when it cannot carry a payload or header injection."""
    if raw and _SAFE_ID.fullmatch(raw.strip()):
        return raw.strip()
    return new_request_id()


def set_request_id(value: str) -> None:
    _REQUEST_ID.set(value)


def get_request_id() -> str:
    return _REQUEST_ID.get()


def set_user_label(value: str | None) -> None:
    _USER_LABEL.set(value or "-")


def get_user_label() -> str:
    return _USER_LABEL.get()
