"""Stop a test from calling the live Gemini API by accident."""

import pytest


@pytest.fixture(autouse=True)
def forbid_live_gemini(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("real Gemini client constructed")

    monkeypatch.setattr("google.genai.Client", refuse)
    monkeypatch.setattr("app.ai.client.build_client", refuse)
