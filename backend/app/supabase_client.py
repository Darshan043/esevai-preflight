"""Small helper for Supabase REST and Storage calls.

The service-role key bypasses row-level security. It stays on the server.
This module never logs request headers, file paths, or signed URLs.
"""

from typing import Any
from urllib.parse import quote

import httpx

from app.config import settings

DOCUMENTS_BUCKET = "documents"


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


def _send(
    method: str,
    url: str,
    headers: dict[str, str],
    *,
    params: dict[str, str] | None = None,
    content: bytes | None = None,
    json_body: Any = None,
) -> httpx.Response:
    """Send one request. Callers must not log the headers or the URL token."""
    try:
        return httpx.request(
            method,
            url,
            headers=headers,
            params=params,
            content=content,
            json=json_body,
            timeout=60.0,
        )
    except httpx.HTTPError as exc:
        raise SupabaseRequestError("The Supabase request could not be completed.") from exc


def _error_text(response: httpx.Response, service_key: str) -> str:
    # Do not include headers. Strip the key if Supabase echoes it in the body.
    return response.text[:180].replace(service_key, "[redacted]")


def _raise_for_status(response: httpx.Response, service_key: str) -> None:
    if response.status_code >= 400:
        raise SupabaseRequestError(
            f"Supabase returned status {response.status_code}. {_error_text(response, service_key)}"
        )


def _request(method: str, url: str, headers: dict[str, str], params: dict[str, str] | None) -> Any:
    response = _send(method, url, headers, params=params)
    _raise_for_status(response, headers.get("apikey", ""))
    if not response.content:
        return None
    return response.json()


def _object_path(path: str) -> str:
    """Encode each path piece so a filename cannot change the storage URL."""
    parts = [quote(part, safe="") for part in path.split("/") if part and part not in {".", ".."}]
    if not parts:
        raise SupabaseRequestError("The storage path is empty.")
    return "/".join(parts)


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


def insert_row(table: str, row: dict[str, Any]) -> dict[str, Any]:
    """Insert one row and return it. The service-role key bypasses row-level security."""
    base_url, service_key = _settings()
    headers = _headers(service_key)
    headers["Content-Type"] = "application/json"
    headers["Prefer"] = "return=representation"
    response = _send("POST", f"{base_url}/rest/v1/{table}", headers, json_body=row)
    _raise_for_status(response, service_key)
    payload = response.json()
    if isinstance(payload, list) and payload and isinstance(payload[0], dict):
        return payload[0]
    raise SupabaseRequestError(f"Supabase did not return the new {table} row.")


def update_rows(table: str, match: dict[str, str], values: dict[str, Any]) -> list[dict[str, Any]]:
    """Update rows selected by match, which uses PostgREST filters such as eq.<id>."""
    base_url, service_key = _settings()
    headers = _headers(service_key)
    headers["Content-Type"] = "application/json"
    headers["Prefer"] = "return=representation"
    response = _send("PATCH", f"{base_url}/rest/v1/{table}", headers, params=match, json_body=values)
    _raise_for_status(response, service_key)
    payload = response.json()
    if not isinstance(payload, list):
        raise SupabaseRequestError(f"Supabase returned an unexpected payload for {table}.")
    return [item for item in payload if isinstance(item, dict)]


def delete_rows(table: str, match: dict[str, str]) -> None:
    """Delete rows selected by match. Missing rows are not an error."""
    base_url, service_key = _settings()
    headers = _headers(service_key)
    headers["Prefer"] = "return=minimal"
    response = _send("DELETE", f"{base_url}/rest/v1/{table}", headers, params=match)
    if response.status_code in {200, 204, 404}:
        return
    _raise_for_status(response, service_key)


def upload_object(path: str, content_bytes: bytes, content_type: str) -> None:
    """Store bytes in the private documents bucket. Fails if that path already exists."""
    base_url, service_key = _settings()
    headers = _headers(service_key)
    headers["Content-Type"] = content_type
    headers["x-upsert"] = "false"
    url = f"{base_url}/storage/v1/object/{DOCUMENTS_BUCKET}/{_object_path(path)}"
    response = _send("POST", url, headers, content=content_bytes)
    if response.status_code in {200, 201}:
        return
    if response.status_code == 409 or "already exists" in response.text.lower():
        raise SupabaseRequestError("A file already exists at that storage path.")
    _raise_for_status(response, service_key)


def delete_objects(paths: list[str]) -> None:
    """Delete storage objects. A path that is already gone is ignored."""
    cleaned = [path for path in paths if path]
    if not cleaned:
        return
    base_url, service_key = _settings()
    headers = _headers(service_key)
    headers["Content-Type"] = "application/json"
    url = f"{base_url}/storage/v1/object/{DOCUMENTS_BUCKET}"
    response = _send("DELETE", url, headers, json_body={"prefixes": cleaned})
    if response.status_code in {200, 204, 404}:
        return
    if "not found" in response.text.lower():
        return
    _raise_for_status(response, service_key)


def absolute_signed_url(base_url: str, signed: str) -> str:
    """Turn Storage's signedURL value into a full address."""
    if signed.startswith("http://") or signed.startswith("https://"):
        return signed
    if not signed.startswith("/"):
        signed = f"/{signed}"
    return f"{base_url.rstrip('/')}/storage/v1{signed}"


def create_signed_url(path: str, expires_in: int = 300) -> str:
    """Ask Storage for a short-lived link. The link is not logged."""
    base_url, service_key = _settings()
    headers = _headers(service_key)
    headers["Content-Type"] = "application/json"
    url = f"{base_url}/storage/v1/object/sign/{DOCUMENTS_BUCKET}/{_object_path(path)}"
    response = _send("POST", url, headers, json_body={"expiresIn": expires_in})
    _raise_for_status(response, service_key)
    payload = response.json()
    if not isinstance(payload, dict):
        raise SupabaseRequestError("Supabase did not return a signed URL.")
    signed = payload.get("signedURL")
    if not isinstance(signed, str) or not signed:
        signed = payload.get("signedUrl")
    if not isinstance(signed, str) or not signed:
        raise SupabaseRequestError("Supabase did not return a signed URL.")
    return absolute_signed_url(base_url, signed)
