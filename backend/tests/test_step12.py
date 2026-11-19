"""Step 12: errors, logs, production checks, limits, retention, and ready."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request

from app.config import settings
from app.errors import GENERIC_500, unhandled_exception_handler
from app.limits.ratelimit import prune_and_allow
from app.logging_safe import redact_text
from app.main import app, create_app
from app.ready import classify_ready, ready_body
from app.request_context import set_request_id
from app.retention import cleanup_expired, cutoff_stamp
from app.startup import origin_is_unsafe, production_problems, validate_settings
from tests.helpers import api_error, api_message
from tests.test_auth import USER_ID, _token, _use_local_tokens

client = TestClient(app)


def _request() -> Request:
    return Request({"type": "http", "method": "GET", "path": "/health", "headers": []})


def test_unauthenticated_uses_error_envelope() -> None:
    response = client.get("/me")
    assert response.status_code == 401
    body = response.json()
    assert "detail" not in body or "error" in body
    error = api_error(response)
    assert error["code"] == "UNAUTHORIZED"
    assert "token" in error["message"].lower()
    assert error["request_id"]
    assert response.headers.get("x-request-id") == error["request_id"]


def test_unknown_route_is_not_found_envelope() -> None:
    response = client.get("/this-route-does-not-exist")
    assert response.status_code == 404
    error = api_error(response)
    assert error["code"] == "NOT_FOUND"
    assert error["request_id"]


def test_incoming_request_id_is_kept_when_safe() -> None:
    response = client.get("/health", headers={"X-Request-ID": "abcDEF12-safe-id"})
    assert response.status_code == 200
    assert response.headers.get("x-request-id") == "abcDEF12-safe-id"


def test_incoming_request_id_is_replaced_when_unsafe() -> None:
    response = client.get("/health", headers={"X-Request-ID": "not safe id with spaces"})
    assert response.status_code == 200
    assert response.headers.get("x-request-id")
    assert " " not in response.headers["x-request-id"]


def test_unhandled_error_is_generic_and_has_request_id() -> None:
    set_request_id("reqid1234567890")
    response = asyncio.run(unhandled_exception_handler(_request(), RuntimeError("sk-ant-secret eyJaaa.bbb.ccc")))
    assert response.status_code == 500
    payload = response.body
    assert GENERIC_500.encode() in payload
    assert b"sk-ant" not in payload
    assert b"eyJaaa" not in payload
    assert b"reqid1234567890" in payload


def test_redact_filter_strips_secrets() -> None:
    text = "token eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.aaa.bbb key sk-ant-abc123 id 123456789012 card 1234567890123456"
    cleaned = redact_text(text)
    assert "eyJ" not in cleaned
    assert "sk-ant-" not in cleaned
    assert "123456789012" not in cleaned
    assert "1234567890123456" not in cleaned
    assert "[redacted-jwt]" in cleaned
    assert "[redacted-key]" in cleaned
    assert cleaned.count("[redacted-number]") == 2


def test_request_log_line_has_no_query_string(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO, logger="esevai.request"):
        client.get("/health?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.aaa.bbb")
    joined = " ".join(record.getMessage() for record in caplog.records)
    assert "eyJ" not in joined
    assert "token=" not in joined
    assert "method=GET" in joined
    assert "status=200" in joined


def test_sliding_window_prunes_and_blocks() -> None:
    kept, allowed, retry = prune_and_allow([8.0, 9.0, 9.5], now=10.0, limit=3, window_seconds=5)
    assert allowed is False
    assert retry >= 1
    kept, allowed, retry = prune_and_allow([1.0], now=10.0, limit=3, window_seconds=5)
    assert allowed is True
    assert kept == [10.0]


def test_production_refuses_missing_and_unsafe_settings() -> None:
    dummy = SimpleNamespace(
        ENVIRONMENT="production",
        SUPABASE_URL="",
        SUPABASE_SERVICE_ROLE_KEY="",
        ALLOWED_ORIGINS="*",
        AI_ENABLED=True,
        GEMINI_API_KEY="",
        GEMINI_MODEL="",
    )
    names = production_problems(dummy)
    assert "SUPABASE_URL" in names
    assert "SUPABASE_SERVICE_ROLE_KEY" in names
    assert "ALLOWED_ORIGINS" in names
    assert "GEMINI_API_KEY" in names
    assert "GEMINI_MODEL" in names
    with pytest.raises(RuntimeError) as caught:
        validate_settings(dummy)
    message = str(caught.value)
    assert "SUPABASE_URL" in message
    assert "*" not in message or "ALLOWED_ORIGINS" in message
    assert "sk-" not in message


def test_localhost_origin_is_unsafe_in_production() -> None:
    assert origin_is_unsafe("http://localhost:3000")
    assert origin_is_unsafe("http://127.0.0.1:3000")
    assert origin_is_unsafe("https://app.example.com") is False


def test_docs_are_off_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "ENABLE_DOCS", "")
    monkeypatch.setattr(settings, "SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setattr(settings, "SUPABASE_SERVICE_ROLE_KEY", "service-role")
    monkeypatch.setattr(settings, "ALLOWED_ORIGINS", "https://app.example.com")
    monkeypatch.setattr(settings, "AI_ENABLED", False)
    production = TestClient(create_app())
    assert production.get("/docs").status_code == 404
    assert production.get("/openapi.json").status_code == 404
    assert production.get("/health").status_code == 200
    assert production.get("/health").headers.get("x-content-type-options") == "nosniff"
    assert production.get("/health").headers.get("x-frame-options") == "DENY"
    assert "max-age=" in (production.get("/health").headers.get("strict-transport-security") or "")


def test_ready_classifies_required_and_optional() -> None:
    status, label = classify_ready(
        {"database": "ok", "storage": "ok", "ocr": "ok"},
        {"tamil_ocr": "yes"},
    )
    assert status == 200 and label == "ok"
    status, label = classify_ready(
        {"database": "fail", "storage": "ok", "ocr": "ok"},
        {"tamil_ocr": "yes"},
    )
    assert status == 503 and label == "degraded"
    status, label = classify_ready(
        {"database": "ok", "storage": "ok", "ocr": "ok"},
        {"tamil_ocr": "no"},
    )
    assert status == 200 and label == "degraded"


def test_ready_endpoint_uses_injected_checks(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.routers.health.ready_body",
        lambda: (200, {"status": "ok", "checks": {"database": "ok", "storage": "ok", "ocr": "ok", "tamil_ocr": "yes"}}),
    )
    response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_ready_rate_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "RATE_LIMIT_READY_PER_MINUTE", 1)
    monkeypatch.setattr(
        "app.routers.health.ready_body",
        lambda: (200, {"status": "ok", "checks": {"database": "ok", "storage": "ok", "ocr": "ok", "tamil_ocr": "yes"}}),
    )
    first = client.get("/health/ready")
    second = client.get("/health/ready")
    assert first.status_code == 200
    assert second.status_code == 429
    assert second.headers.get("retry-after")
    assert api_error(second)["code"] == "RATE_LIMITED"
    assert "wait" in api_message(second).lower()


def test_json_body_too_large() -> None:
    response = client.post("/me", headers={"Content-Length": str(2 * 1024 * 1024)}, content=b"{}")
    assert response.status_code == 413
    assert api_error(response)["code"] == "PAYLOAD_TOO_LARGE"


def test_upload_body_too_large() -> None:
    response = client.post(
        f"/applications/{USER_ID}/documents/{USER_ID}",
        headers={"Content-Length": str(8 * 1024 * 1024)},
        content=b"x",
    )
    assert response.status_code == 413
    assert "large" in api_message(response).lower()


def test_cutoff_uses_updated_at_window() -> None:
    now = datetime(2026, 11, 19, tzinfo=timezone.utc)
    assert cutoff_stamp(30, now) == (now - timedelta(days=30)).isoformat()


def test_cleanup_deletes_storage_before_row() -> None:
    order: list[str] = []

    def reader(table: str, params: dict[str, str]) -> list[dict[str, str]]:
        if table == "applications":
            return [{"id": "app-1", "updated_at": "2020-01-01T00:00:00+00:00"}]
        return [{"id": "file-1", "application_id": "app-1", "storage_path": "hidden/path.jpg"}]

    def remove_objects(paths: list[str]) -> None:
        order.append("storage")
        assert paths == ["hidden/path.jpg"]

    def remove_rows(table: str, match: dict[str, str]) -> None:
        order.append("row")
        assert table == "applications"
        assert match["id"] == "eq.app-1"

    result = cleanup_expired(
        dry_run=False,
        days=30,
        reader=reader,
        remove_objects=remove_objects,
        remove_rows=remove_rows,
        now=datetime(2026, 11, 19, tzinfo=timezone.utc),
    )
    assert order == ["storage", "row"]
    assert result["deleted_applications"] == 1
    assert result["deleted_files"] == 1
    assert result["skipped_applications"] == 0


def test_cleanup_leaves_row_when_storage_fails() -> None:
    from app.supabase_client import SupabaseRequestError

    def reader(table: str, params: dict[str, str]) -> list[dict[str, str]]:
        if table == "applications":
            return [{"id": "app-1", "updated_at": "2020-01-01T00:00:00+00:00"}]
        return [{"id": "file-1", "application_id": "app-1", "storage_path": "hidden/path.jpg"}]

    def remove_objects(_paths: list[str]) -> None:
        raise SupabaseRequestError("storage failed")

    def remove_rows(_table: str, _match: dict[str, str]) -> None:
        raise AssertionError("row must not be deleted")

    result = cleanup_expired(
        dry_run=False,
        days=30,
        reader=reader,
        remove_objects=remove_objects,
        remove_rows=remove_rows,
        now=datetime(2026, 11, 19, tzinfo=timezone.utc),
    )
    assert result["deleted_applications"] == 0
    assert result["skipped_applications"] == 1


def test_cleanup_dry_run_does_not_delete() -> None:
    def reader(table: str, params: dict[str, str]) -> list[dict[str, str]]:
        if table == "applications":
            return [{"id": "app-1", "updated_at": "2020-01-01T00:00:00+00:00"}]
        return [{"id": "file-1", "application_id": "app-1", "storage_path": "hidden/path.jpg"}]

    result = cleanup_expired(
        dry_run=True,
        days=30,
        reader=reader,
        remove_objects=lambda _paths: (_ for _ in ()).throw(AssertionError("no delete")),
        remove_rows=lambda _t, _m: (_ for _ in ()).throw(AssertionError("no delete")),
        now=datetime(2026, 11, 19, tzinfo=timezone.utc),
    )
    assert result["dry_run"] is True
    assert result["applications"] == 1
    assert result["files"] == 1
    assert result["deleted_applications"] == 0


def test_cleanup_admin_requires_auth() -> None:
    response = client.post("/admin/cleanup", json={"dry_run": True})
    assert response.status_code == 401


def test_cleanup_admin_dry_run(monkeypatch: pytest.MonkeyPatch) -> None:
    _use_local_tokens(monkeypatch, "admin")
    monkeypatch.setattr(
        "app.routers.maintenance.cleanup_expired",
        lambda dry_run=True: {"dry_run": dry_run, "days": 30, "applications": 2, "files": 4, "deleted_applications": 0, "deleted_files": 0, "skipped_applications": 0},
    )
    response = client.post("/admin/cleanup", headers={"Authorization": f"Bearer {_token()}"}, json={})
    assert response.status_code == 200
    body = response.json()
    assert body["dry_run"] is True
    assert body["applications"] == 2
    assert "path" not in str(body).lower()


def test_ready_body_helper_uses_callbacks() -> None:
    status, body = ready_body(
        database=lambda: "ok",
        storage=lambda: "ok",
        ocr=lambda: "ok",
        tamil=lambda: "yes",
    )
    assert status == 200
    assert body["checks"]["tamil_ocr"] == "yes"
