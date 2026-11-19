"""Readiness scoring, report builder, and report endpoints. Supabase is mocked."""

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.main import app
from app.report.builder import build_report, sanitise_text
from app.report.scoring import (
    ALMOST_READY_MIN_SCORE,
    FAIL_PENALTY,
    READY_MIN_SCORE,
    WARNING_PENALTY,
    compute_readiness,
    overall_score,
    readiness_label,
    score_one_document,
)
from app.supabase_client import SupabaseRequestError
from tests.helpers import api_message
from tests.test_auth import USER_ID, _token, _use_local_tokens
from tests.test_documents import APP_ID, REQUIRED_ID, UPLOAD_ID, _auth, _install, _send
from tests.test_documents import Store as DocStore
from tests.test_processing import _patch_pipeline, _row
from tests.test_validation import SERVICE_ID

client = TestClient(app)
NOW = datetime(2026, 11, 18, 12, 0, tzinfo=timezone.utc)
OTHER_USER = "99999999-9999-9999-9999-999999999999"


def _required(
    code: str,
    *,
    mandatory: bool = True,
    sort_order: int = 1,
    name_en: str | None = None,
    name_ta: str | None = None,
) -> dict[str, object]:
    return {
        "id": f"req-{code}",
        "code": code,
        "name_en": name_en or code.replace("_", " ").title(),
        "name_ta": name_ta,
        "is_mandatory": mandatory,
        "is_active": True,
        "sort_order": sort_order,
    }


def _upload(code: str, *, status: str = "processed") -> dict[str, object]:
    return {
        "id": f"upload-{code}",
        "required_document_id": f"req-{code}",
        "status": status,
        "updated_at": "2026-11-18T10:00:00+00:00",
        "created_at": "2026-11-18T10:00:00+00:00",
        "storage_path": f"secret/{code}.jpg",
        "ocr_text_masked": "Name: Hidden Person 123456789012",
    }


def _result(
    code: str,
    status: str,
    *,
    upload: str | None = None,
    message: str = "Check message",
    fix: str = "Fix this",
    check_code: str | None = None,
) -> dict[str, object]:
    return {
        "check_code": check_code or f"{code}_{status}",
        "status": status,
        "message": message,
        "fix_suggestion": fix,
        "uploaded_document_id": f"upload-{upload}" if upload else None,
    }


def test_all_pass_is_100_and_ready() -> None:
    required = [_required("photo"), _required("id_card", sort_order=2)]
    uploads = [_upload("photo"), _upload("id_card")]
    results = [
        _result("photo", "pass", upload="photo"),
        _result("id_card", "pass", upload="id_card"),
    ]
    found = compute_readiness(required, uploads, results)
    assert found["score"] == 100
    assert found["label"] == "ready"


def test_one_warning_lowers_a_document_by_10() -> None:
    assert score_one_document(is_mandatory=True, uploaded=True, fail_count=0, warning_count=1) == 100 - WARNING_PENALTY


def test_one_fail_lowers_a_document_by_40() -> None:
    assert score_one_document(is_mandatory=True, uploaded=True, fail_count=1, warning_count=0) == 100 - FAIL_PENALTY


def test_mandatory_missing_scores_0_and_blocks_ready() -> None:
    required = [_required("photo"), _required("id_card", sort_order=2)]
    uploads = [_upload("photo")]
    results = [
        _result("photo", "pass", upload="photo"),
        _result("id_card", "fail", check_code="missing_document", message="ID card is missing."),
    ]
    found = compute_readiness(required, uploads, results)
    assert found["document_scores"]["req-id_card"] == 0
    assert found["score"] < READY_MIN_SCORE or found["label"] != "ready"
    assert found["label"] == "not_ready"
    assert found["missing_mandatory"] == 1


def test_optional_missing_is_excluded_from_the_average() -> None:
    required = [_required("photo"), _required("extra", mandatory=False, sort_order=2)]
    uploads = [_upload("photo")]
    results = [_result("photo", "pass", upload="photo")]
    found = compute_readiness(required, uploads, results)
    assert found["document_scores"]["req-extra"] is None
    assert found["score"] == 100
    assert found["label"] == "ready"


def test_weighted_average_matches_hand_calculation() -> None:
    # Mandatory 60 (weight 2) + mandatory 100 (weight 2) + optional 90 (weight 1)
    # = (120 + 200 + 90) / 5 = 82.
    required = [
        _required("photo"),
        _required("id_card", sort_order=2),
        _required("extra", mandatory=False, sort_order=3),
    ]
    uploads = [_upload("photo"), _upload("id_card"), _upload("extra")]
    results = [
        _result("photo", "fail", upload="photo"),
        _result("id_card", "pass", upload="id_card"),
        _result("extra", "warning", upload="extra"),
    ]
    found = compute_readiness(required, uploads, results)
    assert found["document_scores"]["req-photo"] == 60
    assert found["document_scores"]["req-id_card"] == 100
    assert found["document_scores"]["req-extra"] == 90
    assert found["score"] == 82


def test_cross_document_penalties_and_floor() -> None:
    after_fail = overall_score([(100, 2)], cross_fail=1, cross_warning=0)
    after_warning = overall_score([(100, 2)], cross_fail=0, cross_warning=1)
    assert after_fail == 85
    assert after_warning == 95
    assert overall_score([(0, 2)], cross_fail=4, cross_warning=4) == 0


def test_label_boundaries_and_fail_blocks_ready() -> None:
    assert readiness_label(score=READY_MIN_SCORE, fail_count=0, missing_mandatory=0) == "ready"
    assert readiness_label(score=READY_MIN_SCORE - 1, fail_count=0, missing_mandatory=0) == "almost_ready"
    assert readiness_label(score=ALMOST_READY_MIN_SCORE, fail_count=0, missing_mandatory=0) == "almost_ready"
    assert readiness_label(score=ALMOST_READY_MIN_SCORE - 1, fail_count=0, missing_mandatory=0) == "not_ready"
    assert readiness_label(score=100, fail_count=1, missing_mandatory=0) != "ready"
    assert readiness_label(score=90, fail_count=2, missing_mandatory=0) == "almost_ready"
    assert readiness_label(score=90, fail_count=3, missing_mandatory=0) == "not_ready"


def test_rounding_uses_nearest_integer() -> None:
    # (100 * 2 + 90 * 1) / 3 = 96.666... -> 97
    assert overall_score([(100, 2), (90, 1)], cross_fail=0, cross_warning=0) == 97


def _built() -> dict[str, object]:
    required = [
        _required("photo", sort_order=1, name_en="Passport photo", name_ta="புகைப்படம்"),
        _required("id_card", sort_order=2, name_en="ID card"),
        _required("address", sort_order=3, name_en="Address proof"),
        _required("extra", mandatory=False, sort_order=4, name_en="Optional note"),
    ]
    uploads = [_upload("photo"), _upload("address")]
    results = [
        _result("photo", "fail", upload="photo", message="The photo is blurry.", fix="Upload a sharper photo."),
        _result("address", "warning", upload="address", message="The date is hard to read.", fix="Upload a clearer copy."),
        _result("id_card", "fail", check_code="missing_document", message="ID card is missing.", fix="Upload the ID card."),
        _result("names", "fail", message="Names do not match across documents.", fix="Upload documents for the same person."),
        _result("shared", "warning", message="Check the address lines.", fix="Confirm the address is the same."),
    ]
    return build_report({}, {}, required, uploads, results, NOW)


def test_next_steps_order_dedup_and_carry_list() -> None:
    report = _built()
    types = [step["type"] for step in report["next_steps"]]
    assert types[0] == "missing"
    assert "Get or upload: ID card" == report["next_steps"][0]["text"]
    assert types[1] == "document_fail"
    assert types[2] == "application_fail"
    assert "warning" in types
    assert types[-1] == "carry"
    assert report["next_steps"][-1]["text"] == "Carry the ORIGINAL documents to the e-Sevai centre"
    texts = [step["text"] for step in report["next_steps"]]
    assert len(texts) == len(set(texts))
    carry = [item["name_en"] for item in report["carry_list"]]
    assert carry == ["Passport photo", "ID card", "Address proof", "Optional note"]
    assert report["carry_list"][0]["is_mandatory"] is True
    assert report["carry_list"][-1]["is_mandatory"] is False


def test_document_states_and_privacy() -> None:
    report = _built()
    by_code = {item["code"]: item for item in report["documents"]}
    assert by_code["photo"]["state"] == "needs_fix"
    assert by_code["id_card"]["state"] == "missing"
    assert by_code["address"]["state"] == "check_advised"
    assert by_code["extra"]["state"] == "missing"
    dumped = str(report)
    assert "Hidden Person" not in dumped
    assert "secret/" not in dumped
    assert "storage_path" not in dumped
    assert "123456789012" not in dumped


def test_sanitiser_strips_long_numbers_and_urls() -> None:
    cleaned = sanitise_text("See https://example.test/x and 123456789012 and 1234567890123456 please")
    assert "https://" not in cleaned
    assert "example.test" not in cleaned
    assert "123456789012" not in cleaned
    assert "1234567890123456" not in cleaned
    assert "See" in cleaned
    assert "please" in cleaned


def test_max_twelve_next_steps_merges_the_remainder() -> None:
    required = [_required(f"doc{index}", sort_order=index) for index in range(1, 16)]
    uploads = [_upload(f"doc{index}") for index in range(1, 16)]
    results = [
        _result(f"doc{index}", "warning", upload=f"doc{index}", message=f"Warning {index}", fix=f"Fix {index}")
        for index in range(1, 16)
    ]
    report = build_report({}, {}, required, uploads, results, NOW)
    assert len(report["next_steps"]) == 12
    assert report["next_steps"][-1]["type"] == "carry"
    assert report["next_steps"][-2]["text"] == "Also review the remaining warnings"


class ReportStore:
    def __init__(self) -> None:
        self.application: dict[str, object] = {
            "id": APP_ID,
            "user_id": USER_ID,
            "service_id": SERVICE_ID,
            "status": "draft",
            "readiness_score": None,
            "summary": {"kept": True, "ai_advice": {"items": [{"id": "old", "explanation": "old"}]}},
        }
        self.service = {"id": SERVICE_ID, "name_en": "Community Certificate", "name_ta": None, "slug": "community-certificate"}
        self.required: list[dict[str, object]] = [
            {
                "id": "req-photo",
                "code": "photo",
                "name_en": "Photo",
                "name_ta": "புகைப்படம்",
                "is_mandatory": True,
                "is_active": True,
                "keywords": {"en": [], "ta": []},
                "required_fields": [],
                "rules": {"min_blur_score": 80},
                "validity_days": None,
                "sort_order": 1,
            }
        ]
        self.uploads: list[dict[str, object]] = [
            {
                "id": "upload-photo",
                "required_document_id": "req-photo",
                "status": "processed",
                "quality_metrics": {"blur_score": 400, "width": 800, "height": 1000, "brightness_mean": 140, "skew_angle_degrees": 0, "is_probably_blank": False, "ocr_mean_confidence": 90, "ocr_word_count": 20},
                "ocr_text_masked": "",
                "storage_path": "secret/path.jpg",
                "updated_at": "2020-01-01T00:00:00+00:00",
                "created_at": "2020-01-01T00:00:00+00:00",
            }
        ]
        self.results: list[dict[str, object]] = []
        self.fail_save = False
        self.updates: list[dict[str, object]] = []


def _install_report(monkeypatch: object, store: ReportStore) -> None:
    _use_local_tokens(monkeypatch, "citizen")

    def get_rows(table: str, params: dict[str, str]) -> list[dict[str, object]]:
        if table == "applications":
            if params.get("id") != f"eq.{APP_ID}":
                return []
            if "user_id" in params and params.get("user_id") != f"eq.{USER_ID}":
                return []
            return [dict(store.application)]
        if table == "services":
            return [dict(store.service)]
        if table == "required_documents":
            return list(store.required)
        if table == "uploaded_documents":
            return list(store.uploads)
        if table == "validation_results":
            return list(store.results)
        return []

    def insert_rows(table: str, rows: list[dict[str, object]]) -> list[dict[str, object]]:
        del table
        created = []
        for index, row in enumerate(rows):
            saved = {"id": f"result-{len(store.results) + index + 1}", "created_at": "2026-11-18T12:00:00Z", **row}
            created.append(saved)
        store.results.extend(created)
        return created

    def delete_rows(table: str, match: dict[str, str]) -> None:
        del table
        if match.get("id", "").startswith("not.in."):
            kept = match["id"][len("not.in.(") : -1].split(",")
            store.results = [row for row in store.results if str(row.get("id")) in kept]
            return
        if "application_id" in match:
            store.results = []

    def update_rows(table: str, match: dict[str, str], values: dict[str, object]) -> list[dict[str, object]]:
        del match
        if store.fail_save and table == "applications" and "readiness_score" in values:
            raise SupabaseRequestError("save failed")
        if table == "applications":
            store.application.update(values)
            store.updates.append(dict(values))
            return [dict(store.application)]
        return []

    monkeypatch.setattr("app.routers.report.get_rows", get_rows)
    monkeypatch.setattr("app.routers.report.update_rows", update_rows)
    monkeypatch.setattr("app.routers.validation.get_rows", get_rows)
    monkeypatch.setattr("app.routers.validation.update_rows", update_rows)
    monkeypatch.setattr("app.routers.validation.insert_rows", insert_rows)
    monkeypatch.setattr("app.routers.validation.delete_rows", delete_rows)


def test_report_requires_a_token() -> None:
    assert client.post(f"/applications/{APP_ID}/report").status_code == 401
    assert client.get(f"/applications/{APP_ID}/report").status_code == 401


def test_foreign_application_report_is_404(monkeypatch: object) -> None:
    _install_report(monkeypatch, ReportStore())
    headers = {"Authorization": f"Bearer {_token({'sub': OTHER_USER})}"}
    assert client.post(f"/applications/{APP_ID}/report", headers=headers).status_code == 404
    assert client.get(f"/applications/{APP_ID}/report", headers=headers).status_code == 404


def test_report_without_uploads_is_400(monkeypatch: object) -> None:
    store = ReportStore()
    store.uploads = []
    _install_report(monkeypatch, store)
    response = client.post(f"/applications/{APP_ID}/report", headers={"Authorization": f"Bearer {_token()}"})
    assert response.status_code == 400
    assert "Upload at least one document first" in api_message(response)


def test_report_while_reading_is_409(monkeypatch: object) -> None:
    store = ReportStore()
    store.uploads[0]["status"] = "processing"
    _install_report(monkeypatch, store)
    busy = client.post(f"/applications/{APP_ID}/report", headers={"Authorization": f"Bearer {_token()}"})
    assert busy.status_code == 409
    store.uploads[0]["status"] = "uploaded"
    waiting = client.post(f"/applications/{APP_ID}/report", headers={"Authorization": f"Bearer {_token()}"})
    assert waiting.status_code == 409


def test_successful_report_saves_score_and_preserves_keys(monkeypatch: object) -> None:
    store = ReportStore()
    _install_report(monkeypatch, store)
    headers = {"Authorization": f"Bearer {_token()}"}
    response = client.post(f"/applications/{APP_ID}/report", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["score"] == store.application["readiness_score"]
    assert store.application["status"] == "checked"
    assert store.application["summary"]["kept"] is True
    assert "report" in store.application["summary"]
    assert "ai_advice" not in store.application["summary"]
    assert "storage_path" not in response.text
    assert "secret/path" not in response.text
    assert "eyJ" not in response.text
    listed = client.get(f"/applications/{APP_ID}/report", headers=headers)
    assert listed.status_code == 200
    assert listed.json()["report"]["score"] == body["score"]
    assert listed.json()["is_current"] is True
    second = client.post(f"/applications/{APP_ID}/report", headers=headers)
    assert second.status_code == 200
    assert isinstance(store.application["summary"]["report"], dict)


def test_failed_save_leaves_previous_state(monkeypatch: object) -> None:
    store = ReportStore()
    store.application["status"] = "draft"
    store.application["readiness_score"] = None
    store.fail_save = True
    _install_report(monkeypatch, store)
    response = client.post(f"/applications/{APP_ID}/report", headers={"Authorization": f"Bearer {_token()}"})
    assert response.status_code == 502
    assert store.application["status"] == "draft"
    assert store.application["readiness_score"] is None
    assert "report" not in store.application["summary"]


def test_get_after_stale_clear_returns_null(monkeypatch: object) -> None:
    store = ReportStore()
    _install_report(monkeypatch, store)
    headers = {"Authorization": f"Bearer {_token()}"}
    created = client.post(f"/applications/{APP_ID}/report", headers=headers)
    assert created.status_code == 200
    store.uploads[0]["updated_at"] = "2099-01-01T00:00:00+00:00"
    stale = client.get(f"/applications/{APP_ID}/report", headers=headers)
    assert stale.json()["is_current"] is False
    store.application["summary"] = {"kept": True}
    store.application["readiness_score"] = None
    store.application["status"] = "draft"
    missing = client.get(f"/applications/{APP_ID}/report", headers=headers)
    assert missing.json() == {"report": None, "is_current": False}


def test_replace_delete_and_process_clear_the_report(monkeypatch: object) -> None:
    store = DocStore()
    store.row = {
        "id": UPLOAD_ID,
        "application_id": APP_ID,
        "required_document_id": REQUIRED_ID,
        "user_id": USER_ID,
        "storage_path": f"{USER_ID}/{APP_ID}/photo-old-old.jpg",
        "original_filename": "old.jpg",
        "mime_type": "image/jpeg",
        "size_bytes": 4,
        "status": "processed",
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
        "quality_metrics": {},
        "ocr_text_masked": "hello",
        "extracted_fields": {},
    }
    _install(monkeypatch, store)
    replaced = _send("new.png", b"\x89PNG\r\n\x1a\nrest", "image/png")
    assert replaced.status_code == 200
    assert store.application["status"] == "draft"
    assert store.application["readiness_score"] is None
    assert "report" not in store.application["summary"]
    assert store.application["summary"]["kept"] is True

    store.application["status"] = "checked"
    store.application["readiness_score"] = 88
    store.application["summary"] = {"report": {"score": 88}, "kept": True}
    deleted = client.delete(f"/documents/{UPLOAD_ID}", headers=_auth())
    assert deleted.status_code == 204
    assert store.application["status"] == "draft"
    assert store.application["readiness_score"] is None
    assert "report" not in store.application["summary"]

    store.row = _row(application_id=APP_ID)
    store.application["status"] = "checked"
    store.application["readiness_score"] = 70
    store.application["summary"] = {"report": {"score": 70}, "kept": True}
    _patch_pipeline(monkeypatch, store, {"quality_metrics": {}, "ocr_text_masked": "hello"})
    processed = client.post(f"/documents/{store.row['id']}/process", headers=_auth())
    assert processed.status_code == 200
    assert store.application["status"] == "draft"
    assert store.application["readiness_score"] is None
    assert "report" not in store.application["summary"]
    assert store.application["summary"]["kept"] is True
