"""Small helper for Supabase REST calls.

The service-role key bypasses row-level security. It stays on the server.
This module never logs request headers.
"""

from typing import Any

import httpx

from app.config import settings


class SupabaseConfigError(RuntimeError):
    """Raised when the backend .env file is missing a required Supabase value."""


class SupabaseRequestError(RuntimeError):
    """Raised when Supabase answers with an error status."""


def _settings() -> tuple[str, str]:
    base_url = settings.SUPABASE_URL.strip().rstrip("/")
    service_key = settings.SUPABASE_SERVICE_ROLE_KEY.strip()
    if not base_url or not service_key:
        raise SupabaseConfigError(
            "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in backend/.env."
        )
    return base_url, service_key


def _headers(service_key: str, bearer_token: str | None = None) -> dict[str, str]:
    # The apikey header identifies this server. The bearer token, when set,
    # is the signed-in user's access token rather than the service-role key.
    return {
        "apikey": service_key,
        "Authorization": f"Bearer {bearer_token or service_key}",
        "Accept": "application/json",
    }


def _request(method: str, url: str, headers: dict[str, str], params: dict[str, str] | None) -> Any:
    service_key = headers.get("apikey", "")
    try:
        response = httpx.request(method, url, headers=headers, params=params, timeout=20.0)
    except httpx.HTTPError as exc:
        raise SupabaseRequestError("The Supabase request could not be completed.") from exc
    if response.status_code >= 400:
        # Do not include headers. Strip the key if Supabase echoes it in the body.
        body = response.text[:180].replace(service_key, "[redacted]")
        raise SupabaseRequestError(f"Supabase returned status {response.status_code}. {body}")
    if not response.content:
        return None
    return response.json()


def get_rows(table: str, params: dict[str, str]) -> list[dict[str, Any]]:
    """Read rows from a public table. Returns a list, which may be empty."""
    base_url, service_key = _settings()
    payload = _request(
        "GET",
        f"{base_url}/rest/v1/{table}",
        _headers(service_key),
        params,
    )
    if not isinstance(payload, list):
        raise SupabaseRequestError(f"Supabase returned an unexpected payload for {table}.")
    return payload


def get_auth_user(access_token: str) -> dict[str, Any]:
    """Ask Supabase Auth who owns this access token."""
    base_url, service_key = _settings()
    payload = _request(
        "GET",
        f"{base_url}/auth/v1/user",
        _headers(service_key, bearer_token=access_token),
        None,
    )
    if not isinstance(payload, dict):
        raise SupabaseRequestError("Supabase Auth returned an unexpected payload.")
    return payload
