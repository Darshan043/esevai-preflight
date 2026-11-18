"""Smoke-test categories. The Gemini client is always replaced, so nothing calls Google."""

import logging
from types import SimpleNamespace

import pytest

from app.ai.client import AIUnavailableError, complete_json
from scripts.ai_smoke_test import SMOKE_MAX_OUTPUT_TOKENS, main, smoke_outcome


@pytest.fixture(autouse=True)
def forbid_real_gemini_client(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse() -> None:
        raise AssertionError("real Gemini client constructed")

    monkeypatch.setattr("app.ai.client.build_client", refuse)


def test_ok_reply_is_success() -> None:
    assert smoke_outcome("OK") == "success"
    assert smoke_outcome('{"reply":"ok"}') == "success"


def test_empty_http_200_is_empty_response() -> None:
    assert smoke_outcome("") == "empty_response"
    assert smoke_outcome("   ") == "empty_response"


def test_non_empty_miss_is_not_network() -> None:
    assert smoke_outcome("hello") == "unexpected_response"


def test_main_prints_success(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    def fake_complete(*_args: object, **kwargs: object) -> tuple[str, dict[str, int]]:
        assert kwargs["max_tokens"] == SMOKE_MAX_OUTPUT_TOKENS
        assert kwargs["max_tokens"] >= 64
        return "OK", {"prompt_tokens": 13, "output_tokens": 2}

    monkeypatch.setattr("scripts.ai_smoke_test.complete_json", fake_complete)
    assert main() == 0
    assert capsys.readouterr().out.splitlines()[-1] == "success"


def test_main_prints_empty_response(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(
        "scripts.ai_smoke_test.complete_json",
        lambda *_args, **_kwargs: ("", {"prompt_tokens": 13, "output_tokens": 0}),
    )
    assert main() == 1
    lines = capsys.readouterr().out.splitlines()
    assert lines[-2:] == ["failure", "empty_response"]


def test_main_prints_api_category(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    def fail(*_args: object, **_kwargs: object) -> tuple[str, dict[str, int]]:
        raise AIUnavailableError("network")

    monkeypatch.setattr("scripts.ai_smoke_test.complete_json", fail)
    assert main() == 1
    lines = capsys.readouterr().out.splitlines()
    assert lines[-2:] == ["failure", "network"]


def _install_client(monkeypatch: pytest.MonkeyPatch, generate) -> None:
    monkeypatch.setattr(
        "app.ai.client.build_client",
        lambda: SimpleNamespace(models=SimpleNamespace(generate_content=generate)),
    )


def test_empty_200_is_returned_not_raised(monkeypatch: pytest.MonkeyPatch) -> None:
    response = SimpleNamespace(text="", usage_metadata=SimpleNamespace(prompt_token_count=13, candidates_token_count=0))

    def generate(**_kwargs: object) -> SimpleNamespace:
        return response

    _install_client(monkeypatch, generate)
    text, usage = complete_json("system", "user", max_tokens=SMOKE_MAX_OUTPUT_TOKENS)
    assert text == ""
    assert usage == {"prompt_tokens": 13, "output_tokens": 0}
    assert smoke_outcome(text) == "empty_response"


def test_unavailable_is_network_and_retries_once(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    calls = {"count": 0}

    def generate(**_kwargs: object) -> None:
        calls["count"] += 1
        raise _ApiError(503, "UNAVAILABLE")

    _install_client(monkeypatch, generate)
    with caplog.at_level(logging.WARNING), pytest.raises(AIUnavailableError) as caught:
        complete_json("system", "user", max_tokens=16)
    assert caught.value.category == "network"
    assert caught.value.status_code == 503
    assert calls["count"] == 2
    warnings = [record for record in caplog.records if record.levelno == logging.WARNING]
    assert len(warnings) == 2
    for record in warnings:
        message = record.getMessage()
        assert "category=network" in message
        assert "http_status=503" in message
        assert "api error" not in message
        assert "UNAVAILABLE" not in message


def test_short_429_is_rate_limited_and_retried_once(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    calls = {"count": 0}
    details = {
        "error": {
            "code": 429,
            "message": "SECRET_PROVIDER_TEXT",
            "status": "RESOURCE_EXHAUSTED",
            "details": [
                {"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "20s"},
                {
                    "@type": "type.googleapis.com/google.rpc.QuotaFailure",
                    "violations": [{"quotaId": "GenerateRequestsPerMinutePerProjectPerModel", "quotaMetric": "requests"}],
                },
            ],
        }
    }

    def generate(**_kwargs: object) -> None:
        calls["count"] += 1
        raise _ApiError(429, "RESOURCE_EXHAUSTED", details, "SECRET_PROVIDER_TEXT")

    _install_client(monkeypatch, generate)
    with caplog.at_level(logging.WARNING), pytest.raises(AIUnavailableError) as caught:
        complete_json("system", "user", max_tokens=16)
    assert caught.value.category == "rate limited"
    assert caught.value.status_code == 429
    assert calls["count"] == 2
    assert "SECRET_PROVIDER_TEXT" not in caplog.text


def test_daily_quota_is_not_retried(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"count": 0}
    details = {
        "error": {
            "status": "RESOURCE_EXHAUSTED",
            "details": [
                {"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "20s"},
                {
                    "@type": "type.googleapis.com/google.rpc.QuotaFailure",
                    "violations": [{"quotaId": "GenerateContentInputTokensPerModelPerDay"}],
                },
            ],
        }
    }

    def generate(**_kwargs: object) -> None:
        calls["count"] += 1
        raise _ApiError(429, "RESOURCE_EXHAUSTED", details)

    _install_client(monkeypatch, generate)
    with pytest.raises(AIUnavailableError) as caught:
        complete_json("system", "user")
    assert caught.value.category == "no credit or quota"
    assert caught.value.status_code == 503
    assert calls["count"] == 1


def test_bare_resource_exhausted_is_not_retried(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"count": 0}

    def generate(**_kwargs: object) -> None:
        calls["count"] += 1
        raise _ApiError(429, "RESOURCE_EXHAUSTED")

    _install_client(monkeypatch, generate)
    with pytest.raises(AIUnavailableError) as caught:
        complete_json("system", "user")
    assert caught.value.category == "no credit or quota"
    assert calls["count"] == 1


def test_plain_429_is_still_retried_once(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"count": 0}

    def generate(**_kwargs: object) -> None:
        calls["count"] += 1
        raise _ApiError(429, "")

    _install_client(monkeypatch, generate)
    with pytest.raises(AIUnavailableError) as caught:
        complete_json("system", "user")
    assert caught.value.category == "rate limited"
    assert calls["count"] == 2


def test_invalid_key_is_not_retried(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"count": 0}

    def generate(**_kwargs: object) -> None:
        calls["count"] += 1
        raise _ApiError(401, "UNAUTHENTICATED")

    _install_client(monkeypatch, generate)
    with pytest.raises(AIUnavailableError) as caught:
        complete_json("system", "user")
    assert caught.value.category == "invalid key"
    assert calls["count"] == 1


def test_production_call_does_not_set_thinking_level(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, object] = {}

    def generate(**kwargs: object) -> SimpleNamespace:
        seen["config"] = kwargs["config"]
        return SimpleNamespace(
            text="OK",
            usage_metadata=SimpleNamespace(prompt_token_count=1, candidates_token_count=1),
        )

    _install_client(monkeypatch, generate)
    complete_json("system", "user")
    config = seen["config"]
    assert config.thinking_config is None
    assert config.max_output_tokens == 800


class _ApiError(Exception):
    def __init__(self, code: int, status: str, details: dict[str, object] | None = None, message: str = "api error") -> None:
        self.code = code
        self.status = status
        self.details = details
        super().__init__(message)
