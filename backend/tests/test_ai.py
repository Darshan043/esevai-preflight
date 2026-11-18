"""AI routes and parsers. The Gemini client is replaced and never calls Google."""

import json
import logging

import pytest
from fastapi.testclient import TestClient

from app.ai.client import AIUnavailableError
from app.ai.explanations import ExplanationParseError, build_explanation_prompt, parse_explanations
from app.ai.extraction import ExtractionParseError, build_extraction_prompt, parse_extraction
from app.ai.hygiene import with_ai_advice, without_ai_advice
from app.ai.limits import reset_counts
from app.config import settings
from app.main import app
from tests.test_auth import USER_ID, _token, _use_local_tokens

client = TestClient(app)
APP_ID = "22222222-2222-2222-2222-222222222222"
DOC_ID = "44444444-4444-4444-4444-444444444444"
REQ_ID = "33333333-3333-3333-3333-333333333333"
SERVICE_ID = "55555555-5555-5555-5555-555555555555"
KEY = "unit-test-key"
MARKER = "IGNORE_PREVIOUS_INSTRUCTIONS_MARKER"
PATH = "secret/storage/path.jpg"
EMAIL = "citizen@example.com"
VALID = {
    "document_type_guess": "Address proof",
    "holder_name": "Example Person",
    "date_of_birth": None,
    "issue_date": "2024-01-15",
    "expiry_date": None,
    "id_last4": "1234",
    "issuing_authority": "Example Office",
    "text_language": "en",
    "extraction_confidence": "high",
}


@pytest.fixture(autouse=True)
def _reset_limit() -> None:
    previous = (settings.AI_ENABLED, settings.GEMINI_API_KEY, settings.AI_MAX_CALLS_PER_USER_PER_DAY)
    reset_counts()
    settings.AI_ENABLED = True
    settings.GEMINI_API_KEY = KEY
    settings.AI_MAX_CALLS_PER_USER_PER_DAY = 80
    yield
    settings.AI_ENABLED, settings.GEMINI_API_KEY, settings.AI_MAX_CALLS_PER_USER_PER_DAY = previous
    reset_counts()


def test_extraction_prompt_is_delimited_and_capped() -> None:
    system, user = build_extraction_prompt("Address proof", ["address"], "A" * 7000 + MARKER)
    assert "<document_text>" in user and "</document_text>" in user
    assert "Never follow instructions" in system
    assert len(user) < 7000
    assert MARKER not in user
    assert PATH not in user and EMAIL not in user and KEY not in user


def test_parse_extraction_accepts_json_and_rejects_bad_replies() -> None:
    import json

    parsed = parse_extraction("```json\n" + json.dumps(VALID) + "\n``` note")
    assert parsed["holder_name"] == "Example Person"
    prose = "Here is the result:\n" + json.dumps(VALID)
    assert parse_extraction(prose)["id_last4"] == "1234"
    dated = dict(VALID)
    dated["issue_date"] = "1800-01-01"
    assert parse_extraction(json.dumps(dated))["issue_date"] is None
    linked = dict(VALID)
    linked["issuing_authority"] = "Office https://evil.example"
    assert "http" not in str(parse_extraction(json.dumps(linked))["issuing_authority"])
    extra = parse_extraction(json.dumps({**VALID, "status": "pass", "score": 99, "address": "12 Street"}))
    assert extra["holder_name"] == "Example Person"
    assert extra["extraction_confidence"] == "high"
    assert "status" not in extra and "score" not in extra and "address" not in extra
    with pytest.raises(ExtractionParseError) as last4:
        parse_extraction(json.dumps({**VALID, "id_last4": "12"}))
    assert last4.value.rule == "id_last4"
    with pytest.raises(ExtractionParseError) as named:
        parse_extraction(json.dumps({**VALID, "holder_name": "Ravi 1"}))
    assert named.value.rule == "holder_name"
    with pytest.raises(ExtractionParseError) as broken:
        parse_extraction("this is not json")
    assert broken.value.rule == "json"


def test_parse_extraction_rejects_invalid_known_fields() -> None:
    import json

    missing = dict(VALID)
    del missing["extraction_confidence"]
    with pytest.raises(ExtractionParseError) as required:
        parse_extraction(json.dumps(missing))
    assert required.value.rule == "missing_extraction_confidence"
    with pytest.raises(ExtractionParseError) as confidence:
        parse_extraction(json.dumps({**VALID, "extraction_confidence": "sure"}))
    assert confidence.value.rule == "extraction_confidence"
    with pytest.raises(ExtractionParseError) as expiry:
        parse_extraction(json.dumps({**VALID, "expiry_date": "15-06-2024"}))
    assert expiry.value.rule == "expiry_date"
    with pytest.raises(ExtractionParseError) as malformed:
        parse_extraction("{")
    assert malformed.value.rule == "json"


def test_explanation_prompt_skips_passes_and_drops_private_fields() -> None:
    system, user = build_explanation_prompt(
        [
            {
                "id": "pass-1",
                "document_name": "Address proof",
                "check_code": "document_type",
                "status": "pass",
                "message": "ok",
                "fix_suggestion": "",
                "ocr_text": MARKER,
                "storage_path": PATH,
                "user_id": USER_ID,
            },
            {
                "id": "warn-1",
                "document_name": "Address proof",
                "check_code": "date_validity",
                "status": "warning",
                "message": "We could not find a date.",
                "fix_suggestion": "Make the date visible.",
                "ocr_text": MARKER,
                "storage_path": PATH,
                "user_id": USER_ID,
            },
        ],
        "ta",
    )
    assert "Tamil" in system
    assert "warn-1" in user
    assert "pass-1" not in user
    assert MARKER not in user and PATH not in user and USER_ID not in user
    parsed = parse_explanations(
        '{"items":[{"id":"warn-1","explanation":"The date is missing. Upload a page that shows it."}],"overall_tip":"Check the page."}',
        {"warn-1"},
    )
    assert parsed["items"][0]["id"] == "warn-1"
    cleaned = parse_explanations(
        '{"items":[{"id":"warn-1","explanation":"See https://evil.example for help"}],"overall_tip":null}',
        {"warn-1"},
    )
    assert "http" not in cleaned["items"][0]["explanation"]
    with pytest.raises(ExplanationParseError):
        parse_explanations('{"items":[{"id":"other","explanation":"No"}],"overall_tip":null}', {"warn-1"})
    with pytest.raises(ExplanationParseError):
        parse_explanations(
            '{"items":[{"id":"warn-1","explanation":"' + ("x" * 221) + '"}],"overall_tip":null}',
            {"warn-1"},
        )


def test_summary_merge_keeps_other_keys() -> None:
    merged = with_ai_advice({"kept": True, "ai_advice": {"old": True}}, {"items": []})
    assert merged["kept"] is True
    assert merged["ai_advice"] == {"items": []}
    assert "ai_advice" not in without_ai_advice(merged)


class Store:
    def __init__(self) -> None:
        self.document: dict[str, object] = {
            "id": DOC_ID,
            "application_id": APP_ID,
            "user_id": USER_ID,
            "required_document_id": REQ_ID,
            "status": "processed",
            "ocr_text_masked": f"Name: Example Person\n{MARKER}",
            "extracted_fields": {},
            "updated_at": "2026-11-18T00:00:00Z",
            "storage_path": PATH,
        }
        self.application: dict[str, object] = {
            "id": APP_ID,
            "user_id": USER_ID,
            "service_id": SERVICE_ID,
            "summary": {"kept": True},
        }
        self.results: list[dict[str, object]] = []
        self.calls = 0
        self.prompts: list[str] = []
        self.reply = __import__("json").dumps(VALID)
        self.enabled = True


def _install(monkeypatch: pytest.MonkeyPatch, store: Store) -> None:
    _use_local_tokens(monkeypatch, "citizen")

    def get_rows(table: str, params: dict[str, str]) -> list[dict[str, object]]:
        if table == "uploaded_documents":
            if params.get("user_id") and params.get("user_id") != f"eq.{USER_ID}":
                return []
            if params.get("id") in {f"eq.{DOC_ID}", f"in.({DOC_ID})"}:
                return [store.document]
            return []
        if table == "applications":
            if params.get("user_id") == f"eq.{USER_ID}" and params.get("id") == f"eq.{APP_ID}":
                return [store.application]
            return []
        if table == "required_documents":
            return [{"id": REQ_ID, "service_id": SERVICE_ID, "name_en": "Address proof", "keywords": {"en": ["address"]}}]
        if table == "validation_results":
            return list(store.results)
        return []

    def update_rows(table: str, match: dict[str, str], values: dict[str, object]) -> list[dict[str, object]]:
        del match
        if table == "uploaded_documents":
            store.document.update(values)
            store.document["updated_at"] = "2026-11-18T01:00:00Z"
            return [dict(store.document)]
        if table == "applications":
            store.application.update(values)
            return [dict(store.application)]
        return []

    def complete(system: str, user: str, max_tokens: int | None = None) -> tuple[str, dict[str, int]]:
        del system, max_tokens
        store.calls += 1
        store.prompts.append(user)
        return store.reply, {"prompt_tokens": 11, "output_tokens": 7}

    monkeypatch.setattr("app.routers.ai.get_rows", get_rows)
    monkeypatch.setattr("app.routers.ai.update_rows", update_rows)
    monkeypatch.setattr("app.routers.ai.complete_json", complete)
    monkeypatch.setattr(settings, "AI_ENABLED", True)
    monkeypatch.setattr(settings, "GEMINI_API_KEY", KEY)


def _auth(sub: str = USER_ID) -> dict[str, str]:
    return {"Authorization": f"Bearer {_token({'sub': sub})}"}


def test_ai_routes_require_login() -> None:
    assert client.post(f"/documents/{DOC_ID}/extract").status_code == 401
    assert client.post(f"/applications/{APP_ID}/explain").status_code == 401
    assert client.get(f"/applications/{APP_ID}/ai-advice").status_code == 401


def test_extract_saves_fields_and_cache_skips_the_model(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    store = Store()
    _install(monkeypatch, store)
    with caplog.at_level(logging.INFO):
        first = client.post(f"/documents/{DOC_ID}/extract", headers=_auth())
    assert first.status_code == 200
    assert first.json()["holder_name"] == "Example Person"
    assert "_meta" not in first.json()
    assert store.document["status"] == "processed"
    saved = store.document["extracted_fields"]
    assert isinstance(saved, dict) and saved["_meta"]["source_updated_at"] == "2026-11-18T00:00:00Z"
    second = client.post(f"/documents/{DOC_ID}/extract", headers=_auth())
    assert second.status_code == 200
    assert store.calls == 1
    forced = client.post(f"/documents/{DOC_ID}/extract?force=true", headers=_auth())
    assert forced.status_code == 200
    assert store.calls == 2
    assert KEY not in first.text and MARKER not in first.text and PATH not in first.text
    assert KEY not in caplog.text and MARKER not in caplog.text and PATH not in caplog.text
    assert all(PATH not in prompt and EMAIL not in prompt for prompt in store.prompts)


def test_extract_rejects_unread_and_failed_ai(monkeypatch: pytest.MonkeyPatch) -> None:
    store = Store()
    store.document["status"] = "uploaded"
    store.document["ocr_text_masked"] = None
    _install(monkeypatch, store)
    unread = client.post(f"/documents/{DOC_ID}/extract", headers=_auth())
    assert unread.status_code == 409
    assert unread.json()["detail"] == "Read the document first"
    stranger = client.post(f"/documents/{DOC_ID}/extract", headers=_auth("99999999-9999-9999-9999-999999999999"))
    assert stranger.status_code == 404

    store.document["status"] = "processed"
    store.document["ocr_text_masked"] = "Name: Example Person"
    store.reply = "not json"
    failed = client.post(f"/documents/{DOC_ID}/extract", headers=_auth())
    assert failed.status_code == 502
    assert store.document["extracted_fields"] == {}
    assert KEY not in failed.text
    assert failed.json()["detail"] == (
        "AI could not read the details from this document. Your standard checks still work. You can try AI again."
    )


def test_extract_failure_logs_category_and_status(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    store = Store()
    _install(monkeypatch, store)

    def unavailable(system: str, user: str, max_tokens: int | None = None) -> tuple[str, dict[str, int]]:
        del system, max_tokens
        store.calls += 1
        store.prompts.append(user)
        raise AIUnavailableError("network")

    monkeypatch.setattr("app.routers.ai.complete_json", unavailable)
    with caplog.at_level(logging.WARNING):
        failed = client.post(f"/documents/{DOC_ID}/extract", headers=_auth())
    assert failed.status_code == 503
    assert failed.json()["detail"] == "AI assistance is unavailable right now. Your standard checks still work."
    assert store.document["extracted_fields"] == {}
    warning = _extraction_warning(caplog)
    assert warning.levelno == logging.WARNING
    message = warning.getMessage()
    assert "Gemini document extraction" in message
    assert "category=network" in message
    assert "http_status=503" in message
    assert KEY not in message and MARKER not in message and PATH not in message

    caplog.clear()
    monkeypatch.setattr(
        "app.routers.ai.complete_json",
        lambda *_args, **_kwargs: ("not json", {"prompt_tokens": 1, "output_tokens": 0}),
    )
    with caplog.at_level(logging.WARNING):
        parsed = client.post(f"/documents/{DOC_ID}/extract", headers=_auth())
    assert parsed.status_code == 502
    assert store.document["extracted_fields"] == {}
    parse_warning = _extraction_warning(caplog)
    assert parse_warning.levelno == logging.WARNING
    parse_message = parse_warning.getMessage()
    assert "Gemini document extraction" in parse_message
    assert "category=parse" in parse_message
    assert "http_status=502" in parse_message
    assert "rule=json" in parse_message
    assert KEY not in parse_message and MARKER not in parse_message and PATH not in parse_message
    assert "not json" not in parse_message

    caplog.clear()
    secret_reply = json.dumps(
        {
            **VALID,
            "extraction_confidence": "sure",
            "holder_name": "SECRET_PERSON",
            "note": "SECRET_NOTE",
        }
    )
    monkeypatch.setattr(
        "app.routers.ai.complete_json",
        lambda *_args, **_kwargs: (secret_reply, {"prompt_tokens": 1, "output_tokens": 0}),
    )
    with caplog.at_level(logging.WARNING):
        invalid = client.post(f"/documents/{DOC_ID}/extract", headers=_auth())
    assert invalid.status_code == 502
    assert store.document["extracted_fields"] == {}
    secret_warning = _extraction_warning(caplog)
    secret_message = secret_warning.getMessage()
    assert "category=parse" in secret_message
    assert "rule=extraction_confidence" in secret_message
    assert "SECRET_PERSON" not in secret_message
    assert "SECRET_NOTE" not in caplog.text
    assert "SECRET_PERSON" not in caplog.text
    assert "sure" not in secret_message


def _extraction_warning(caplog: pytest.LogCaptureFixture) -> logging.LogRecord:
    matches = [
        record
        for record in caplog.records
        if record.name == "app.routers.ai" and record.levelno == logging.WARNING
    ]
    assert len(matches) == 1
    return matches[0]


def test_ai_disabled_and_daily_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    store = Store()
    _install(monkeypatch, store)
    monkeypatch.setattr(settings, "AI_ENABLED", False)
    off = client.post(f"/documents/{DOC_ID}/extract", headers=_auth())
    assert off.status_code == 503
    assert off.json()["detail"] == "AI assistance is turned off."
    assert store.calls == 0
    monkeypatch.setattr(settings, "AI_ENABLED", True)
    monkeypatch.setattr(settings, "AI_MAX_CALLS_PER_USER_PER_DAY", 0)
    limited = client.post(f"/documents/{DOC_ID}/extract", headers=_auth())
    assert limited.status_code == 429
    assert store.calls == 0


def test_explain_merges_summary_and_skips_passes(monkeypatch: pytest.MonkeyPatch) -> None:
    store = Store()
    store.results = [
        {
            "id": "pass-1",
            "uploaded_document_id": DOC_ID,
            "check_code": "document_type",
            "status": "pass",
            "message": "Looks right.",
            "fix_suggestion": "",
        }
    ]
    _install(monkeypatch, store)
    empty = client.post(f"/applications/{APP_ID}/explain", headers=_auth(), json={"language": "en"})
    assert empty.status_code == 200
    assert empty.json() == {"items": [], "overall_tip": None}
    assert store.calls == 0

    store.results.append(
        {
            "id": "warn-1",
            "uploaded_document_id": DOC_ID,
            "check_code": "date_validity",
            "status": "warning",
            "message": "We could not find a date.",
            "fix_suggestion": "Show the date.",
        }
    )
    store.reply = '{"items":[{"id":"warn-1","explanation":"The date is not visible. Upload a clearer page."}],"overall_tip":"Check the date."}'
    explained = client.post(f"/applications/{APP_ID}/explain", headers=_auth(), json={"language": "ta"})
    assert explained.status_code == 200
    body = explained.json()
    assert body["language"] == "ta"
    assert body["items"][0]["id"] == "warn-1"
    summary = store.application["summary"]
    assert isinstance(summary, dict) and summary["kept"] is True
    assert summary["ai_advice"]["items"][0]["explanation"].startswith("The date")
    assert "pass-1" not in store.prompts[-1]
    saved = client.get(f"/applications/{APP_ID}/ai-advice", headers=_auth())
    assert saved.status_code == 200
    assert saved.json()["overall_tip"] == "Check the date."
    assert client.get(f"/applications/{APP_ID}/ai-advice", headers=_auth("99999999-9999-9999-9999-999999999999")).status_code == 404


def test_explain_distinguishes_rate_limit_quota_and_daily_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    store = Store()
    store.results = [
        {
            "id": "warn-1",
            "uploaded_document_id": DOC_ID,
            "check_code": "date_validity",
            "status": "warning",
            "message": "We could not find a date.",
            "fix_suggestion": "Show the date.",
        }
    ]
    _install(monkeypatch, store)

    def raise_category(category: str):
        def fail(system: str, user: str, max_tokens: int | None = None) -> tuple[str, dict[str, int]]:
            del system, max_tokens
            store.calls += 1
            store.prompts.append(user)
            raise AIUnavailableError(category)

        return fail

    monkeypatch.setattr("app.routers.ai.complete_json", raise_category("rate limited"))
    busy = client.post(f"/applications/{APP_ID}/explain", headers=_auth(), json={"language": "en"})
    assert busy.status_code == 429
    assert busy.json()["detail"] == "AI is busy; try again after a short wait."
    assert "quota" not in busy.json()["detail"]
    assert store.application["summary"] == {"kept": True}

    monkeypatch.setattr("app.routers.ai.complete_json", raise_category("no credit or quota"))
    quota = client.post(f"/applications/{APP_ID}/explain", headers=_auth(), json={"language": "en"})
    assert quota.status_code == 503
    assert quota.json()["detail"] == (
        "AI assistance is temporarily unavailable due to the provider's quota. Standard checks still work."
    )
    assert store.application["summary"] == {"kept": True}

    monkeypatch.setattr(settings, "AI_MAX_CALLS_PER_USER_PER_DAY", 0)
    calls_before = store.calls
    daily = client.post(f"/applications/{APP_ID}/explain", headers=_auth(), json={"language": "en"})
    assert daily.status_code == 429
    assert daily.json()["detail"] == "The daily AI limit has been reached. Please try again tomorrow."
    assert store.calls == calls_before


def test_validate_and_process_clear_saved_advice(monkeypatch: pytest.MonkeyPatch) -> None:
    cleared: list[str] = []

    def spy(application_id: str, **_kwargs: object) -> None:
        cleared.append(application_id)

    monkeypatch.setattr("app.routers.validation.clear_ai_advice", spy)
    monkeypatch.setattr("app.routers.documents.clear_ai_advice", spy)
    from tests.test_documents import APP_ID as DOC_APP
    from tests.test_documents import _install as install_documents
    from tests.test_documents import Store as DocStore
    from tests.test_processing import _patch_pipeline, _row

    doc_store = DocStore()
    doc_store.row = _row(application_id=DOC_APP)
    _patch_pipeline(monkeypatch, doc_store, {"quality_metrics": {}, "ocr_text_masked": "hello"})
    response = client.post(f"/documents/{doc_store.row['id']}/process", headers={"Authorization": f"Bearer {_token()}"})
    assert response.status_code == 200
    assert DOC_APP in cleared
    from tests.test_validation import _install as install_validation
    from tests.test_validation import Store as ValStore

    install_validation(monkeypatch, ValStore())
    checked = client.post(f"/applications/{DOC_APP}/validate", headers={"Authorization": f"Bearer {_token()}"})
    assert checked.status_code == 200
    assert cleared.count(DOC_APP) >= 2
