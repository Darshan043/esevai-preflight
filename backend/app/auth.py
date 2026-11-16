"""Check Supabase access tokens and load the caller's profile role.

The role always comes from the profiles table. A value inside the token is ignored.
"""

from typing import Any

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient
from jwt.exceptions import PyJWTError

from app.config import settings
from app.supabase_client import SupabaseRequestError, get_auth_user, get_rows

# Missing Authorization header becomes None so we can return our own 401 JSON.
bearer_scheme = HTTPBearer(auto_error=False)

# Reuse the public signing keys for a few minutes instead of fetching them every request.
_JWKS_TTL_SECONDS = 300
_jwks_client: PyJWKClient | None = None
_jwks_url: str | None = None


class CurrentUser:
    """The signed-in person, after the token and the profile row have been checked."""

    def __init__(
        self,
        user_id: str,
        email: str | None,
        role: str,
        full_name: str | None,
        preferred_language: str | None,
    ) -> None:
        self.user_id = user_id
        self.email = email
        self.role = role
        self.full_name = full_name
        self.preferred_language = preferred_language

    def as_dict(self) -> dict[str, str | None]:
        return {
            "user_id": self.user_id,
            "email": self.email,
            "role": self.role,
            "full_name": self.full_name,
            "preferred_language": self.preferred_language,
        }


class TokenVerificationError(Exception):
    """The token could not be checked locally. The Auth server fallback may still run."""


def _unauthorized(message: str) -> HTTPException:
    return HTTPException(status_code=401, detail=message)


def _jwks() -> PyJWKClient:
    """Build a cached client for the project's public JWKS document."""
    global _jwks_client, _jwks_url
    base_url = settings.SUPABASE_URL.strip().rstrip("/")
    if not base_url:
        raise TokenVerificationError("SUPABASE_URL is not set.")
    url = f"{base_url}/auth/v1/.well-known/jwks.json"
    if _jwks_client is None or _jwks_url != url:
        _jwks_client = PyJWKClient(url, cache_jwk_set=True, lifespan=_JWKS_TTL_SECONDS)
        _jwks_url = url
    return _jwks_client


def _decode_locally(token: str) -> dict[str, Any]:
    """Verify the signature, expiry, audience, and subject without trusting the token body."""
    try:
        header = jwt.get_unverified_header(token)
    except PyJWTError as exc:
        raise TokenVerificationError("The token could not be read.") from exc

    algorithm = header.get("alg")
    if not isinstance(algorithm, str) or algorithm.lower() == "none":
        # "none" would skip the signature. Reject it before any fallback.
        raise HTTPException(status_code=401, detail="The login token is invalid or expired.")

    try:
        if algorithm == "HS256":
            secret = settings.SUPABASE_JWT_SECRET.strip()
            if not secret:
                raise TokenVerificationError("SUPABASE_JWT_SECRET is not set.")
            claims = jwt.decode(
                token,
                secret,
                algorithms=["HS256"],
                audience="authenticated",
                options={"require": ["exp", "sub"]},
            )
        elif algorithm in {"ES256", "RS256"}:
            signing_key = _jwks().get_signing_key_from_jwt(token).key
            claims = jwt.decode(
                token,
                signing_key,
                algorithms=[algorithm],
                audience="authenticated",
                options={"require": ["exp", "sub"]},
            )
        else:
            raise TokenVerificationError(f"Unsupported signing algorithm {algorithm}.")
    except HTTPException:
        raise
    except PyJWTError as exc:
        raise TokenVerificationError("Local token verification failed.") from exc

    if not isinstance(claims, dict) or not claims.get("sub"):
        raise TokenVerificationError("The token has no subject.")
    return claims


def confirm_token_with_auth_server(token: str) -> dict[str, Any]:
    """Ask Supabase Auth to accept or reject the access token.

    Local HS256 and JWKS checks fail when the project has rotated its signing
    key, or when SUPABASE_JWT_SECRET does not match the token. Auth still
    knows which sessions are valid, so this last check uses that answer.
    The service-role key is sent only as the apikey header. The user's token
    stays in Authorization.
    """
    try:
        payload = get_auth_user(token)
    except SupabaseRequestError as exc:
        raise _unauthorized("The login token is invalid or expired.") from exc
    user_id = payload.get("id")
    if not user_id:
        raise _unauthorized("The login token is invalid or expired.")
    email = payload.get("email")
    return {"sub": str(user_id), "email": email if isinstance(email, str) else None}


def decode_access_token(token: str) -> dict[str, Any]:
    """Return the trusted claims, using the Auth server only when local checks fail."""
    try:
        return _decode_locally(token)
    except HTTPException:
        raise
    except TokenVerificationError:
        return confirm_token_with_auth_server(token)


def lookup_profile(user_id: str) -> dict[str, Any] | None:
    """Load the profile row. The role in this row is the only role we trust."""
    rows = get_rows(
        "profiles",
        {"id": f"eq.{user_id}", "select": "full_name,role,preferred_language"},
    )
    if not rows:
        return None
    return rows[0]


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> CurrentUser:
    """FastAPI dependency for routes that require a signed-in user."""
    if credentials is None or credentials.scheme.lower() != "bearer" or not credentials.credentials:
        raise _unauthorized("A login token is required.")

    claims = decode_access_token(credentials.credentials)
    user_id = claims.get("sub")
    if not isinstance(user_id, str) or not user_id:
        raise _unauthorized("The login token is invalid or expired.")

    try:
        profile = lookup_profile(user_id)
    except SupabaseRequestError as exc:
        raise HTTPException(status_code=403, detail="The profile could not be loaded.") from exc
    if profile is None or not isinstance(profile.get("role"), str):
        raise HTTPException(status_code=403, detail="No profile exists for this account.")

    email = claims.get("email")
    full_name = profile.get("full_name")
    language = profile.get("preferred_language")
    return CurrentUser(
        user_id=user_id,
        email=email if isinstance(email, str) else None,
        role=profile["role"],
        full_name=full_name if isinstance(full_name, str) else None,
        preferred_language=language if isinstance(language, str) else None,
    )


def require_admin(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    """FastAPI dependency for routes that only an admin may call."""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access is required.")
    return user
