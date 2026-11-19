"""Owner-run smoke test for the local or deployed app.

This script does not create database or storage rows. It only reads public
pages and unauthenticated API answers.

The agent must not run the live path. Use --selftest only.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

DEFAULT_FRONTEND = "http://127.0.0.1:3000"
DEFAULT_BACKEND = "http://127.0.0.1:8000"


class SmokeFailure(RuntimeError):
    """One check did not match the expected status or JSON shape."""


def _get(url: str, timeout: float = 15.0) -> tuple[int, dict[str, str], bytes]:
    request = Request(url, method="GET")
    try:
        with urlopen(request, timeout=timeout) as response:
            return response.status, {key.lower(): value for key, value in response.headers.items()}, response.read()
    except HTTPError as exc:
        body = exc.read() if exc.fp else b""
        headers = {key.lower(): value for key, value in (exc.headers.items() if exc.headers else [])}
        return exc.code, headers, body
    except URLError as exc:
        raise SmokeFailure(f"Could not reach {url}.") from exc


def _json(body: bytes) -> Any:
    try:
        return json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SmokeFailure("The response was not JSON.") from exc


def check_health(backend: str) -> None:
    status, _headers, body = _get(f"{backend.rstrip('/')}/health")
    if status != 200:
        raise SmokeFailure(f"/health returned {status}")
    payload = _json(body)
    if payload.get("status") != "ok":
        raise SmokeFailure("/health status was not ok.")


def check_ready(backend: str) -> None:
    status, _headers, body = _get(f"{backend.rstrip('/')}/health/ready")
    if status not in {200, 503}:
        raise SmokeFailure(f"/health/ready returned {status}")
    payload = _json(body)
    if payload.get("status") not in {"ok", "degraded"}:
        raise SmokeFailure("/health/ready status was not ok or degraded.")
    checks = payload.get("checks")
    if not isinstance(checks, dict) or "database" not in checks:
        raise SmokeFailure("/health/ready checks were missing.")


def check_unauthenticated_error(backend: str) -> None:
    status, headers, body = _get(f"{backend.rstrip('/')}/me")
    if status != 401:
        raise SmokeFailure(f"/me without a token returned {status}")
    payload = _json(body)
    error = payload.get("error")
    if not isinstance(error, dict) or not error.get("message") or not error.get("request_id"):
        raise SmokeFailure("/me did not return the error envelope.")
    if not headers.get("x-request-id"):
        raise SmokeFailure("/me did not send X-Request-ID.")
    text = body.decode("utf-8", errors="ignore")
    if "eyJ" in text or "sk-ant-" in text:
        raise SmokeFailure("/me body looked like it contained a secret.")


def check_frontend_home(frontend: str) -> None:
    status, _headers, body = _get(frontend.rstrip("/") + "/")
    if status != 200:
        raise SmokeFailure(f"frontend / returned {status}")
    if b"e-Sevai" not in body and b"esevai" not in body.lower():
        raise SmokeFailure("frontend / did not look like the homepage.")


def run(frontend: str, backend: str) -> None:
    check_health(backend)
    check_ready(backend)
    check_unauthenticated_error(backend)
    check_frontend_home(frontend)
    print("e2e smoke: all checks passed")


def selftest() -> None:
    """Exercise the checks against canned responses. No network."""
    canned = {
        "http://127.0.0.1:8000/health": (
            200,
            {"content-type": "application/json"},
            b'{"status":"ok","service":"esevai-preflight-backend"}',
        ),
        "http://127.0.0.1:8000/health/ready": (
            200,
            {"content-type": "application/json"},
            b'{"status":"ok","checks":{"database":"ok","storage":"ok","ocr":"ok","tamil_ocr":"yes"}}',
        ),
        "http://127.0.0.1:8000/me": (
            401,
            {"content-type": "application/json", "x-request-id": "abc123"},
            b'{"error":{"code":"UNAUTHORIZED","message":"A login token is required.","request_id":"abc123"}}',
        ),
        "http://127.0.0.1:3000/": (200, {"content-type": "text/html"}, b"<html>e-Sevai Pre-Flight</html>"),
    }

    def fake_get(url: str, timeout: float = 15.0) -> tuple[int, dict[str, str], bytes]:
        del timeout
        if url not in canned:
            raise SmokeFailure(f"unexpected url {url}")
        return canned[url]

    global _get
    original = _get
    _get = fake_get
    try:
        run(DEFAULT_FRONTEND, DEFAULT_BACKEND)
    finally:
        _get = original


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only smoke test. Does not create rows.")
    parser.add_argument("--selftest", action="store_true", help="Run against canned responses. No network.")
    parser.add_argument("--frontend", default=os.environ.get("E2E_FRONTEND_URL", DEFAULT_FRONTEND))
    parser.add_argument("--backend", default=os.environ.get("E2E_BACKEND_URL", DEFAULT_BACKEND))
    args = parser.parse_args()
    try:
        if args.selftest:
            selftest()
        else:
            run(args.frontend, args.backend)
    except SmokeFailure as exc:
        print(f"e2e smoke failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
