"""Auth checks that do not call the real Supabase project.

Tokens are signed with a fake test secret. Profile reads are replaced in each test.
"""

import time

import jwt
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app

client = TestClient(app)
TEST_SECRET = "test-only-hs256-secret-with-32bx"
USER_ID = "11111111-1111-1111-1111-111111111111"


def _token(claims: dict[str, object] | None = None, secret: str = TEST_SECRET) -> str:
    payload: dict[str, object] = {
        "sub": USER_ID,
        "aud": "authenticated",
        "email": "citizen@example.com",
        "exp": int(time.time()) + 600,
    }
    if claims:
        payload.update(claims)
    encoded = jwt.encode(payload, secret, algorithm="HS256")
    return encoded if isinstance(encoded, str) else encoded.decode("utf-8")


def _profile(role: str) -> dict[str, str]:
    return {
        "full_name": "Test Citizen",
        "role": role,
        "preferred_language": "en",
    }


def _use_local_tokens(monkeypatch: object, role: str | None) -> None:
    """Point verification at the fake secret and skip the network."""
    monkeypatch.setattr(settings, "SUPABASE_JWT_SECRET", TEST_SECRET)

    def reject_fallback(_token: str) -> dict[str, object]:
        raise HTTPException(status_code=401, detail="The login token is invalid or expired.")

    monkeypatch.setattr("app.auth.confirm_token_with_auth_server", reject_fallback)
    if role is None:
        monkeypatch.setattr("app.auth.lookup_profile", lambda _user_id: None)
    else:
        monkeypatch.setattr("app.auth.lookup_profile", lambda _user_id: _profile(role))


def test_me_without_token_is_401() -> None:
    response = client.get("/me")
    assert response.status_code == 401
    assert "token" in response.json()["detail"].lower()


def test_me_with_garbage_token_is_401(monkeypatch: object) -> None:
    _use_local_tokens(monkeypatch, "citizen")
    response = client.get("/me", headers={"Authorization": "Bearer not-a-token"})
    assert response.status_code == 401


def test_me_with_expired_token_is_401(monkeypatch: object) -> None:
    _use_local_tokens(monkeypatch, "citizen")
    token = _token({"exp": int(time.time()) - 60})
    response = client.get("/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


def test_me_with_wrong_audience_is_401(monkeypatch: object) -> None:
    _use_local_tokens(monkeypatch, "citizen")
    token = _token({"aud": "someone-else"})
    response = client.get("/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


def test_me_with_valid_citizen_is_200(monkeypatch: object) -> None:
    _use_local_tokens(monkeypatch, "citizen")
    response = client.get("/me", headers={"Authorization": f"Bearer {_token()}"})
    body = response.json()
    assert response.status_code == 200
    assert body["user_id"] == USER_ID
    assert body["email"] == "citizen@example.com"
    assert body["role"] == "citizen"
    assert body["full_name"] == "Test Citizen"
    assert body["preferred_language"] == "en"


def test_admin_ping_as_citizen_is_403(monkeypatch: object) -> None:
    _use_local_tokens(monkeypatch, "citizen")
    response = client.get("/admin/ping", headers={"Authorization": f"Bearer {_token()}"})
    assert response.status_code == 403


def test_admin_ping_as_admin_is_200(monkeypatch: object) -> None:
    _use_local_tokens(monkeypatch, "admin")
    response = client.get("/admin/ping", headers={"Authorization": f"Bearer {_token()}"})
    assert response.status_code == 200
    assert response.json() == {"ok": True, "message": "admin access granted"}


def test_admin_ping_without_token_is_401() -> None:
    response = client.get("/admin/ping")
    assert response.status_code == 401


def test_health_stays_public() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
