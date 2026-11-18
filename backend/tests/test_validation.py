"""Validation engine and endpoints. Supabase is mocked. No image files."""

from datetime import date

from fastapi.testclient import TestClient

from app.main import app
from app.supabase_client import SupabaseRequestError
from app.validation.checks import date_validity, document_type, id_number_format, image_quality, required_fields
from app.validation.cross_checks import check_missing_documents, check_name_consistency
from app.validation.engine import validate_application
from app.validation.models import DocumentInput
from tests.test_auth import USER_ID, _token, _use_local_tokens

client = TestClient(app)
APP_ID = "22222222-2222-2222-2222-222222222222"
SERVICE_ID = "55555555-5555-5555-5555-555555555555"
TODAY = date(2026, 11, 17)
MARKER = "UNIQUE_OCR_MARKER"


def _metrics(**extra: object) -> dict[str, object]:
    metrics: dict[str, object] = {
        "width": 1200,
        "height": 1600,
        "blur_score": 500,
        "brightness_mean": 140,
        "skew_angle_degrees": 1,
        "is_probably_blank": False,
        "ocr_mean_confidence": 90,
        "ocr_word_count": 24,
    }
    metrics.update(extra)
    return metrics


def _document(
    code: str,
    *,
    text: str = "Address proof for the household dated 01/11/2026",
    status: str = "processed",
    metrics: dict[str, object] | None = None,
    keywords: object | None = None,
    fields: list[str] | None = None,
    rules: dict[str, object] | None = None,
    mandatory: bool = True,
    validity_days: int | None = None,
    sort_order: int = 1,
    name_en: str | None = None,
    upload_id: str | None = None,
    extracted_fields: dict[str, object] | None = None,
) -> DocumentInput:
    return DocumentInput(
        document_id=upload_id or f"upload-{code}",
        config={
            "id": f"req-{code}",
            "code": code,
            "name_en": name_en or code.replace("_", " "),
            "is_mandatory": mandatory,
            "is_active": True,
            "keywords": {"en": [code.replace("_", " ")]} if keywords is None else keywords,
            "required_fields": [] if fields is None else fields,
            "rules": {} if rules is None else rules,
            "validity_days": validity_days,
            "sort_order": sort_order,
        },
        quality_metrics=_metrics() if metrics is None else metrics,
        ocr_text_masked=text,
        status=status,
        extracted_fields={} if extracted_fields is None else extracted_fields,
    )


def _by_code(results: list, code: str):
    return [item for item in results if item.check_code == code]


def test_image_quality_sharp_blur_size_light_blank_and_photo() -> None:
    sharp = image_quality(_document("photo", keywords={"en": [], "ta": []}, fields=[]))
    assert sharp is not None and sharp.status == "pass"

    blurry = image_quality(_document("page", metrics=_metrics(blur_score=10)))
    assert blurry is not None and blurry.status == "fail"

    small = image_quality(_document("page", metrics=_metrics(width=200, height=200)))
    assert small is not None and small.status == "warning"

    dark = image_quality(_document("page", metrics=_metrics(brightness_mean=10)))
    bright = image_quality(_document("page", metrics=_metrics(brightness_mean=250)))
    paper = image_quality(_document("page", metrics=_metrics(brightness_mean=250, contrast_std=5, is_probably_blank=False)))
    blank_glare = image_quality(_document("page", metrics=_metrics(brightness_mean=250, contrast_std=5, is_probably_blank=True)))
    assert dark is not None and dark.status == "warning"
    assert bright is not None and bright.status == "warning"
    assert paper is not None and paper.status == "pass"
    assert blank_glare is not None and blank_glare.status == "fail"

    blank = image_quality(_document("page", metrics=_metrics(is_probably_blank=True)))
    assert blank is not None and blank.status == "fail"

    unsure = image_quality(_document("page", metrics=_metrics(ocr_mean_confidence=20)))
    assert unsure is not None and unsure.status == "warning"

    photo = image_quality(_document("photo", keywords={"en": [], "ta": []}, fields=[], metrics=_metrics(ocr_mean_confidence=5)))
    assert photo is not None and photo.status == "pass"
    assert photo.details["confidence_low"] is False


def test_document_type_keywords_fuzzy_and_readability() -> None:
    english = document_type(_document("address_proof", text="This address proof was issued for the resident today"))
    tamil = document_type(
        _document("community", keywords={"en": [], "ta": ["சாதி"]}, text="இது சாதி சான்றிதழ் ஆகும் மற்றும் மேலும் சொற்கள் இங்கே உள்ளன today")
    )
    assert english is not None and english.status == "pass"
    assert tamil is not None and tamil.status == "pass"

    fuzzy = document_type(
        _document(
            "address_proof",
            keywords={"en": ["community certificate"]},
            text="Attached communty certifcate for the applicant and extra words so the page is readable enough",
        )
    )
    assert fuzzy is not None and fuzzy.status == "pass"

    unread = document_type(_document("address_proof", text="blur", metrics=_metrics(ocr_mean_confidence=10, ocr_word_count=1)))
    assert unread is not None and unread.status == "warning"

    wrong = document_type(
        _document(
            "address_proof",
            text="A shopping list for rice dal and vegetables bought from the market this morning",
            keywords={"en": ["address proof"]},
        )
    )
    assert wrong is not None and wrong.status == "fail"
    assert "does not look like" in wrong.message


def test_labelled_name_and_date_lines() -> None:
    from app.validation.text_extract import extract_dates, extract_name_candidate

    first = "Full Name: Meena Iyer\nDocument Date: 02-03-2024\nAddress: 8, Lake Road"
    second = "Full Name:\nKarthik Raman\nDocument Date:\n29.08.2025"
    spaced = "Issued 17 - 11 - 2026"
    assert extract_name_candidate(first) == "MEENA IYER"
    assert extract_dates(first) == [date(2024, 3, 2)]
    assert extract_name_candidate(second) == "KARTHIK RAMAN"
    assert extract_dates(second) == [date(2025, 8, 29)]
    assert extract_dates(spaced) == [date(2026, 11, 17)]


def test_required_fields_present_and_missing() -> None:
    complete = _document(
        "address_proof",
        fields=["name", "date", "number"],
        text="Name: Anitha Kumar\nDate: 01/11/2026\nReference 600001",
        metrics=_metrics(masked_id_count=1),
    )
    results = required_fields(complete)
    assert [item.status for item in results] == ["pass", "pass", "pass"]

    missing = required_fields(_document("address_proof", fields=["name", "date", "number"], text="Page 4"))
    assert [item.status for item in missing] == ["warning", "warning", "warning"]


def test_id_number_format_valid_invalid_missing_and_old_count() -> None:
    body = "23456789012"
    inverse = (0, 4, 3, 2, 1, 5, 6, 7, 8, 9)
    multiplication = (
        (0, 1, 2, 3, 4, 5, 6, 7, 8, 9),
        (1, 2, 3, 4, 0, 6, 7, 8, 9, 5),
        (2, 3, 4, 0, 1, 7, 8, 9, 5, 6),
        (3, 4, 0, 1, 2, 8, 9, 5, 6, 7),
        (4, 0, 1, 2, 3, 9, 5, 6, 7, 8),
        (5, 9, 8, 7, 6, 0, 4, 3, 2, 1),
        (6, 5, 9, 8, 7, 1, 0, 4, 3, 2),
        (7, 6, 5, 9, 8, 2, 1, 0, 4, 3),
        (8, 7, 6, 5, 9, 3, 2, 1, 0, 4),
        (9, 8, 7, 6, 5, 4, 3, 2, 1, 0),
    )
    permutation = (
        (0, 1, 2, 3, 4, 5, 6, 7, 8, 9),
        (1, 5, 7, 6, 2, 8, 3, 0, 9, 4),
        (5, 8, 0, 3, 7, 9, 6, 1, 4, 2),
        (8, 9, 1, 6, 0, 4, 3, 5, 2, 7),
        (9, 4, 5, 3, 1, 2, 6, 8, 7, 0),
        (4, 2, 8, 6, 5, 7, 3, 9, 0, 1),
        (2, 7, 9, 3, 8, 0, 6, 4, 1, 5),
        (7, 0, 4, 6, 9, 1, 3, 2, 5, 8),
    )

    def checksum(number: str) -> int:
        check = 0
        for index, char in enumerate(reversed(number)):
            check = multiplication[check][permutation[index % 8][int(char)]]
        return check

    valid = body + str(inverse[checksum(body + "0")])
    rules = {"id_number_pattern": "aadhaar"}
    good = id_number_format(
        _document("id", rules=rules, metrics=_metrics(id_checks=[{"type": "aadhaar", "last4": valid[-4:], "checksum_valid": True}]))
    )
    bad = id_number_format(
        _document("id", rules=rules, metrics=_metrics(id_checks=[{"type": "aadhaar", "last4": "0000", "checksum_valid": False}]))
    )
    none = id_number_format(_document("id", rules=rules, metrics=_metrics(id_checks=[])))
    old = id_number_format(_document("id", rules=rules, metrics=_metrics(masked_id_count=1)))
    assert good is not None and good.status == "pass"
    assert bad is not None and bad.status == "warning"
    assert none is not None and none.status == "warning"
    assert old is not None and old.status == "pass"
    assert valid not in str(good.details)
    assert "0000" in str(bad.details)


def test_date_validity_recent_old_missing_and_future() -> None:
    recent = date_validity(_document("address_proof", text="Issued 01/11/2026", validity_days=90), TODAY)
    old = date_validity(_document("address_proof", text="Issued 01/01/2020", validity_days=90), TODAY)
    missing = date_validity(_document("address_proof", text="No calendar here at all", validity_days=90), TODAY)
    future = date_validity(_document("address_proof", text="Issued 01/12/2026", validity_days=90), TODAY)
    skipped = date_validity(_document("address_proof", text="Issued 01/01/2020"), TODAY)
    assert recent is not None and recent.status == "pass"
    assert old is not None and old.status == "fail"
    assert missing is not None and missing.status == "warning"
    assert future is not None and future.status == "warning"
    assert skipped is None


def test_name_consistency_and_missing_documents() -> None:
    same_left = _document("address_proof", text="Name: Mr Anitha Kumar", rules={"check_name_match": True}, sort_order=1)
    same_right = _document("self_declaration", text="Name: ANITHA   KUMAR", rules={"check_name_match": True}, sort_order=2)
    close_right = _document("self_declaration", text="Name: Anitha K", rules={"check_name_match": True}, sort_order=2)
    other_right = _document("self_declaration", text="Name: Ravi Sharma", rules={"check_name_match": True}, sort_order=2)
    only_one = check_name_consistency([same_left])
    same = check_name_consistency([same_left, same_right])
    close = check_name_consistency([same_left, close_right])
    different = check_name_consistency([same_left, other_right])
    assert only_one is None
    assert same is not None and same.status == "pass"
    assert close is not None and close.status == "warning"
    assert "slightly different" in (close.message or "")
    assert different is not None and different.status == "fail"
    blob = str(different.details)
    assert "Anitha" not in blob and "Ravi" not in blob
    assert "address_proof" in blob and "score" in blob

    photo = {"id": "req-photo", "code": "photo", "name_en": "Photo", "is_mandatory": True, "is_active": True, "sort_order": 1}
    optional = {"id": "req-dnc", "code": "dnc", "name_en": "DNC", "is_mandatory": False, "is_active": True, "sort_order": 2}
    missing = check_missing_documents([photo, optional], [])
    assert len(missing) == 1
    assert missing[0].status == "fail"
    assert missing[0].details == {"required_document_code": "photo"}
    assert missing[0].uploaded_document_id is None


def test_ai_name_is_used_and_low_confidence_falls_back() -> None:
    matched = check_name_consistency(
        [
            _document(
                "address_proof",
                text="Name: OTHER PERSON",
                rules={"check_name_match": True},
                extracted_fields={"holder_name": "Ravi Kumar", "extraction_confidence": "high"},
            ),
            _document(
                "self_declaration",
                text="Name: DIFFERENT NAME",
                rules={"check_name_match": True},
                extracted_fields={"holder_name": "Ravi Kumar", "extraction_confidence": "medium"},
            ),
        ]
    )
    assert matched is not None and matched.status == "pass"

    fallback = check_name_consistency(
        [
            _document("address_proof", text="Name: Ravi Kumar", rules={"check_name_match": True}),
            _document("self_declaration", text="Name: Ravi Kumar", rules={"check_name_match": True}),
        ]
    )
    assert fallback is not None and fallback.status == "pass"

    ignored = check_name_consistency(
        [
            _document(
                "address_proof",
                text="Name: Ravi Kumar",
                rules={"check_name_match": True},
                extracted_fields={"holder_name": "Completely Different", "extraction_confidence": "low"},
            ),
            _document("self_declaration", text="Name: Ravi Kumar", rules={"check_name_match": True}),
        ]
    )
    assert ignored is not None and ignored.status == "pass"
    named = required_fields(
        _document(
            "address_proof",
            text="no name line",
            fields=["name"],
            extracted_fields={"holder_name": "Ravi Kumar", "extraction_confidence": "high"},
        )
    )
    assert named[0].status == "pass" and named[0].details["present"] is True


def test_ai_expiry_fails_and_empty_fields_stay_on_the_heuristic() -> None:
    expired = date_validity(
        _document(
            "address_proof",
            text="No date here",
            extracted_fields={"expiry_date": "2020-01-01", "extraction_confidence": "high"},
        ),
        TODAY,
    )
    assert expired is not None and expired.status == "fail"
    assert expired.details.get("expired") is True

    unchanged = date_validity(
        _document("address_proof", validity_days=3650, extracted_fields={}),
        TODAY,
    )
    assert unchanged is not None and unchanged.status == "pass"

    blurry = image_quality(
        _document(
            "photo",
            metrics=_metrics(blur_score=1),
            keywords={"en": [], "ta": []},
            extracted_fields={"holder_name": "Ravi Kumar", "extraction_confidence": "high"},
        )
    )
    assert blurry is not None and blurry.status == "fail"


def test_engine_status_order_and_privacy() -> None:
    waiting = _document("address_proof", status="uploaded", sort_order=2, text=MARKER)
    broken = _document("self_declaration", status="failed", sort_order=1, text=MARKER)
    ready = _document(
        "community",
        sort_order=3,
        text=f"Name: Anitha Kumar\n{MARKER} community certificate 01/11/2026",
        keywords={"en": ["community certificate"]},
        fields=["name"],
        rules={"check_name_match": True},
        validity_days=365,
    )
    results = validate_application([], [ready, broken, waiting], today=TODAY)
    codes = [(item.sort_order, item.status, item.check_code) for item in results if item.uploaded_document_id]
    assert codes[0][0] == 1 and codes[0][1] == "fail"
    assert any(item.check_code == "document_not_processed" and item.status == "warning" for item in results)
    joined = " ".join(f"{item.message} {item.fix_suggestion} {item.details}" for item in results)
    assert MARKER not in joined


class Store:
    def __init__(self) -> None:
        self.results: list[dict[str, object]] = []
        self.fail_insert = False
        self.uploads: list[dict[str, object]] = []
        self.required: list[dict[str, object]] = [
            {
                "id": "req-photo",
                "code": "photo",
                "name_en": "Photo",
                "is_mandatory": True,
                "is_active": True,
                "keywords": {"en": [], "ta": []},
                "required_fields": [],
                "rules": {"min_blur_score": 80},
                "validity_days": None,
                "sort_order": 1,
            }
        ]


def _install(monkeypatch: object, store: Store) -> None:
    _use_local_tokens(monkeypatch, "citizen")

    def get_rows(table: str, params: dict[str, str]) -> list[dict[str, object]]:
        if table == "applications":
            if params.get("user_id") == f"eq.{USER_ID}" and params.get("id") == f"eq.{APP_ID}":
                return [{"id": APP_ID, "user_id": USER_ID, "service_id": SERVICE_ID}]
            return []
        if table == "required_documents":
            return list(store.required)
        if table == "uploaded_documents":
            return list(store.uploads)
        if table == "validation_results":
            return list(store.results)
        return []

    def insert_rows(table: str, rows: list[dict[str, object]]) -> list[dict[str, object]]:
        del table
        if store.fail_insert:
            raise SupabaseRequestError("insert failed")
        created = []
        for index, row in enumerate(rows):
            saved = {"id": f"result-{len(store.results) + index + 1}", "created_at": "2026-11-17T00:00:00Z", **row}
            created.append(saved)
        store.results.extend(created)
        return created

    def delete_rows(table: str, match: dict[str, str]) -> None:
        del table
        if match.get("id", "").startswith("not.in."):
            kept = match["id"][len("not.in.(") : -1].split(",")
            store.results = [row for row in store.results if str(row.get("id")) in kept]
            return
        if "application_id" in match and "id" not in match:
            store.results = []

    monkeypatch.setattr("app.routers.validation.get_rows", get_rows)
    monkeypatch.setattr("app.routers.validation.insert_rows", insert_rows)
    monkeypatch.setattr("app.routers.validation.delete_rows", delete_rows)


def test_validate_requires_a_token() -> None:
    assert client.post(f"/applications/{APP_ID}/validate").status_code == 401
    assert client.get(f"/applications/{APP_ID}/validation").status_code == 401


def test_other_user_validation_is_404(monkeypatch: object) -> None:
    _install(monkeypatch, Store())
    headers = {"Authorization": f"Bearer {_token({'sub': '99999999-9999-9999-9999-999999999999'})}"}
    assert client.post(f"/applications/{APP_ID}/validate", headers=headers).status_code == 404
    assert client.get(f"/applications/{APP_ID}/validation", headers=headers).status_code == 404


def test_validate_stores_replaces_and_hides_storage_path(monkeypatch: object) -> None:
    store = Store()
    store.uploads = [
        {
            "id": "upload-photo",
            "required_document_id": "req-photo",
            "status": "processed",
            "quality_metrics": _metrics(),
            "ocr_text_masked": "",
            "storage_path": "secret/path.jpg",
        }
    ]
    _install(monkeypatch, store)
    headers = {"Authorization": f"Bearer {_token()}"}
    first = client.post(f"/applications/{APP_ID}/validate", headers=headers)
    assert first.status_code == 200
    body = first.json()
    assert body["summary"]["pass"] >= 1
    assert "storage_path" not in first.text
    assert "secret/path" not in first.text
    saved_count = len(store.results)
    second = client.post(f"/applications/{APP_ID}/validate", headers=headers)
    assert second.status_code == 200
    assert len(store.results) == saved_count
    listed = client.get(f"/applications/{APP_ID}/validation", headers=headers)
    assert listed.status_code == 200
    assert listed.json()["summary"]["pass"] == body["summary"]["pass"]
    assert "storage_path" not in listed.text
