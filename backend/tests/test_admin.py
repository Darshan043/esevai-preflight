"""Admin config, clone, stats, and locks. Supabase is mocked. No network."""

from datetime import date, datetime, timezone

from fastapi.testclient import TestClient

from app.admin.clone import DRAFT_PREFIX, build_clone_payload
from app.admin.config_validation import RequiredDocumentInput, ServiceInput, parse_model
from app.admin.stats import activity, anonymise_user_id, score_summary, top_failure_reasons, totals
from app.main import app
from app.report.builder import build_report
from app.supabase_client import SupabaseRequestError
from app.validation.engine import validate_application
from app.validation.models import DocumentInput
from tests.test_auth import USER_ID, _token, _use_local_tokens

client = TestClient(app)
SERVICE_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
DOC_ID = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
OTHER_DOC = "cccccccc-cccc-cccc-cccc-cccccccccccc"
APP_ID = "dddddddd-dddd-dddd-dddd-dddddddddddd"
MARKER_EMAIL = "secret.person@example.com"
MARKER_NAME = "Hidden Holder Name"
MARKER_OCR = "UNIQUE_OCR_MARKER"
MARKER_PATH = "secret/storage/path.jpg"
MARKER_USER = "11111111-1111-1111-1111-111111111111"

ADMIN_ENDPOINTS = [
    ("GET", "/admin/ping"),
    ("GET", "/admin/services"),
    ("POST", "/admin/services"),
    ("GET", f"/admin/services/{SERVICE_ID}"),
    ("PUT", f"/admin/services/{SERVICE_ID}"),
    ("POST", f"/admin/services/{SERVICE_ID}/duplicate"),
    ("DELETE", f"/admin/services/{SERVICE_ID}"),
    ("POST", f"/admin/services/{SERVICE_ID}/documents"),
    ("PUT", f"/admin/documents/{DOC_ID}"),
    ("DELETE", f"/admin/documents/{DOC_ID}"),
    ("POST", f"/admin/services/{SERVICE_ID}/documents/reorder"),
    ("GET", "/admin/stats"),
    ("GET", "/admin/applications"),
]


def _auth(role: str = "admin", sub: str = USER_ID) -> dict[str, str]:
    return {"Authorization": f"Bearer {_token({'sub': sub})}"}


class Store:
    def __init__(self) -> None:
        self.services: list[dict[str, object]] = [
            {
                "id": SERVICE_ID,
                "slug": "community-certificate",
                "name_en": "Community Certificate",
                "name_ta": None,
                "description": "Original",
                "is_active": True,
                "is_verified": False,
            }
        ]
        self.documents: list[dict[str, object]] = [
            {
                "id": DOC_ID,
                "service_id": SERVICE_ID,
                "code": "photo",
                "name_en": "Photo",
                "name_ta": None,
                "description": None,
                "is_mandatory": True,
                "accepted_formats": ["jpg"],
                "max_size_mb": 5,
                "validity_days": None,
                "keywords": {"en": [], "ta": []},
                "required_fields": [],
                "rules": {"min_blur_score": 80},
                "sort_order": 10,
                "is_active": True,
            }
        ]
        self.applications: list[dict[str, object]] = []
        self.uploads: list[dict[str, object]] = []
        self.profiles: list[dict[str, object]] = [
            {"id": USER_ID, "role": "admin"},
            {"id": "22222222-2222-2222-2222-222222222222", "role": "citizen"},
        ]
        self.results: list[dict[str, object]] = []
        self.fail_next_insert = False
        self.deleted: list[tuple[str, dict[str, str]]] = []


def _install(monkeypatch: object, store: Store, role: str = "admin") -> None:
    _use_local_tokens(monkeypatch, role)

    def get_rows(table: str, params: dict[str, str]) -> list[dict[str, object]]:
        rows: list[dict[str, object]]
        if table == "services":
            rows = list(store.services)
            if params.get("id", "").startswith("eq."):
                wanted = params["id"][3:]
                rows = [row for row in rows if row["id"] == wanted]
            if params.get("slug", "").startswith("eq."):
                wanted = params["slug"][3:]
                rows = [row for row in rows if row.get("slug") == wanted]
        elif table == "required_documents":
            rows = list(store.documents)
            if params.get("id", "").startswith("eq."):
                wanted = params["id"][3:]
                rows = [row for row in rows if row["id"] == wanted]
            if params.get("service_id", "").startswith("eq."):
                wanted = params["service_id"][3:]
                rows = [row for row in rows if row.get("service_id") == wanted]
        elif table == "applications":
            rows = list(store.applications)
            if params.get("service_id", "").startswith("eq."):
                wanted = params["service_id"][3:]
                rows = [row for row in rows if row.get("service_id") == wanted]
        elif table == "uploaded_documents":
            rows = list(store.uploads)
            if params.get("required_document_id", "").startswith("eq."):
                wanted = params["required_document_id"][3:]
                rows = [row for row in rows if row.get("required_document_id") == wanted]
        elif table == "profiles":
            rows = list(store.profiles)
        elif table == "validation_results":
            rows = list(store.results)
        else:
            rows = []
        limit = params.get("limit")
        if limit and limit.isdigit():
            rows = rows[: int(limit)]
        return rows

    def count_rows(table: str, params: dict[str, str] | None = None) -> int:
        return len(get_rows(table, params or {"select": "id"}))

    def insert_row(table: str, row: dict[str, object]) -> dict[str, object]:
        if store.fail_next_insert:
            store.fail_next_insert = False
            raise SupabaseRequestError("insert failed")
        created = {"id": f"new-{table}-{len(store.services)+len(store.documents)}", **row}
        if table == "services":
            if any(item.get("slug") == row.get("slug") for item in store.services):
                raise SupabaseRequestError("duplicate slug status 409")
            store.services.append(created)
        elif table == "required_documents":
            if any(item.get("service_id") == row.get("service_id") and item.get("code") == row.get("code") for item in store.documents):
                raise SupabaseRequestError("duplicate code status 409")
            store.documents.append(created)
        return created

    def insert_rows(table: str, rows: list[dict[str, object]]) -> list[dict[str, object]]:
        if store.fail_next_insert:
            store.fail_next_insert = False
            raise SupabaseRequestError("insert failed")
        return [insert_row(table, row) for row in rows]

    def update_rows(table: str, match: dict[str, str], values: dict[str, object]) -> list[dict[str, object]]:
        rows = get_rows(table, match)
        for row in rows:
            row.update(values)
        return rows

    def delete_rows(table: str, match: dict[str, str]) -> None:
        store.deleted.append((table, dict(match)))
        wanted = match.get("id", "")[3:] if match.get("id", "").startswith("eq.") else ""
        if table == "services":
            store.services = [row for row in store.services if row["id"] != wanted]
            store.documents = [row for row in store.documents if row.get("service_id") != wanted]
        if table == "required_documents":
            store.documents = [row for row in store.documents if row["id"] != wanted]

    monkeypatch.setattr("app.routers.admin_config.get_rows", get_rows)
    monkeypatch.setattr("app.routers.admin_config.count_rows", count_rows)
    monkeypatch.setattr("app.routers.admin_config.insert_row", insert_row)
    monkeypatch.setattr("app.routers.admin_config.insert_rows", insert_rows)
    monkeypatch.setattr("app.routers.admin_config.update_rows", update_rows)
    monkeypatch.setattr("app.routers.admin_config.delete_rows", delete_rows)
    monkeypatch.setattr("app.routers.admin_stats.get_rows", get_rows)
    monkeypatch.setattr("app.routers.admin_stats.count_rows", count_rows)


def test_admin_endpoints_require_admin(monkeypatch: object) -> None:
    store = Store()
    for method, path in ADMIN_ENDPOINTS:
        assert client.request(method, path).status_code == 401
        _install(monkeypatch, store, role="citizen")
        assert client.request(method, path, headers=_auth("citizen"), json={}).status_code == 403
    _install(monkeypatch, store, role="admin")
    assert client.get("/admin/stats", headers=_auth()).status_code == 200
    assert client.get("/admin/services", headers=_auth()).status_code == 200


def test_valid_service_and_document_pass() -> None:
    service, errors = parse_model(
        ServiceInput,
        {"slug": "income-certificate", "name_en": "Income Certificate", "confirm_verified": False},
    )
    assert errors == [] and service is not None
    document, doc_errors = parse_model(
        RequiredDocumentInput,
        {
            "code": "salary_slip",
            "name_en": "Salary slip",
            "accepted_formats": ["pdf", "jpg"],
            "max_size_mb": 5,
            "keywords": {"en": ["salary", "salary"], "ta": []},
            "required_fields": ["name", "date"],
            "rules": {"min_blur_score": 100, "id_number_pattern": "^[0-9]{12}$"},
        },
    )
    assert doc_errors == [] and document is not None
    assert document.keywords["en"] == ["salary"]


def test_config_validation_rejects_bad_values() -> None:
    _, slug_errors = parse_model(ServiceInput, {"slug": "A", "name_en": "X"})
    assert slug_errors
    _, code_errors = parse_model(
        RequiredDocumentInput,
        {"code": "1bad", "name_en": "X", "accepted_formats": ["gif"], "max_size_mb": 9},
    )
    assert code_errors
    _, days_errors = parse_model(
        RequiredDocumentInput,
        {"code": "ok_doc", "name_en": "X", "accepted_formats": ["pdf"], "max_size_mb": 2, "validity_days": 0},
    )
    assert any("validity_days" in item["field"] for item in days_errors)
    _, extra = parse_model(
        RequiredDocumentInput,
        {"code": "ok_doc", "name_en": "X", "accepted_formats": ["pdf"], "max_size_mb": 2, "rules": {"unknown": 1}},
    )
    assert extra
    _, brightness = parse_model(
        RequiredDocumentInput,
        {
            "code": "ok_doc",
            "name_en": "X",
            "accepted_formats": ["pdf"],
            "max_size_mb": 2,
            "rules": {"min_brightness": 200, "max_brightness": 10},
        },
    )
    assert brightness
    _, nested = parse_model(
        RequiredDocumentInput,
        {
            "code": "ok_doc",
            "name_en": "X",
            "accepted_formats": ["pdf"],
            "max_size_mb": 2,
            "keywords": {"en": ["id"]},
            "rules": {"id_number_pattern": "(a+)+"},
        },
    )
    assert nested
    _, invalid = parse_model(
        RequiredDocumentInput,
        {
            "code": "ok_doc",
            "name_en": "X",
            "accepted_formats": ["pdf"],
            "max_size_mb": 2,
            "keywords": {"en": ["id"]},
            "rules": {"id_number_pattern": "["},
        },
    )
    assert invalid
    _, photo = parse_model(
        RequiredDocumentInput,
        {
            "code": "photo",
            "name_en": "Photo",
            "accepted_formats": ["jpg"],
            "max_size_mb": 2,
            "keywords": {"en": [], "ta": []},
            "required_fields": [],
            "rules": {"check_name_match": True},
        },
    )
    assert photo


def test_clone_is_always_a_draft() -> None:
    service, docs = build_clone_payload(
        {"name_ta": "பெயர்", "description": "Live list"},
        [{"code": "photo", "name_en": "Photo", "is_active": True, "sort_order": 1}],
        "income-certificate-demo",
        "Income Certificate (Demo)",
    )
    assert service["is_active"] is False
    assert service["is_verified"] is False
    assert service["description"].startswith(DRAFT_PREFIX)
    assert "id" not in docs[0]


def test_unknown_service_is_404(monkeypatch: object) -> None:
    store = Store()
    _install(monkeypatch, store)
    missing = client.get("/admin/services/00000000-0000-0000-0000-000000000000", headers=_auth())
    assert missing.status_code == 404


def test_create_service_defaults_and_locks(monkeypatch: object) -> None:
    store = Store()
    _install(monkeypatch, store)
    created = client.post(
        "/admin/services",
        headers=_auth(),
        json={"slug": "income-certificate-demo", "name_en": "Income Certificate (Demo)"},
    )
    assert created.status_code == 201
    body = created.json()
    assert body["is_active"] is False
    assert body["is_verified"] is False
    listed = client.get("/admin/services", headers=_auth())
    slugs = [item["slug"] for item in listed.json()["items"]]
    assert "income-certificate-demo" in slugs
    assert "community-certificate" in slugs
    verified = client.post(
        "/admin/services",
        headers=_auth(),
        json={"slug": "verified-one", "name_en": "Verified", "is_verified": True},
    )
    assert verified.status_code == 422
    ok_verified = client.post(
        "/admin/services",
        headers=_auth(),
        json={"slug": "verified-one", "name_en": "Verified", "is_verified": True, "confirm_verified": True},
    )
    assert ok_verified.status_code == 201
    dup = client.post(
        "/admin/services",
        headers=_auth(),
        json={"slug": "community-certificate", "name_en": "Copy"},
    )
    assert dup.status_code == 409
    store.applications.append({"id": APP_ID, "service_id": SERVICE_ID, "user_id": USER_ID})
    locked = client.put(
        f"/admin/services/{SERVICE_ID}",
        headers=_auth(),
        json={"slug": "new-slug", "name_en": "Community Certificate"},
    )
    assert locked.status_code == 409
    blocked = client.delete(f"/admin/services/{SERVICE_ID}", headers=_auth())
    assert blocked.status_code == 409
    store.applications = []
    removed = client.delete(f"/admin/services/{SERVICE_ID}", headers=_auth())
    assert removed.status_code == 204


def test_document_locks_and_reorder(monkeypatch: object) -> None:
    store = Store()
    store.documents.append(
        {
            "id": OTHER_DOC,
            "service_id": SERVICE_ID,
            "code": "address",
            "name_en": "Address",
            "is_active": True,
            "sort_order": 20,
            "accepted_formats": ["pdf"],
            "max_size_mb": 5,
            "keywords": {"en": ["address"], "ta": []},
            "required_fields": ["name"],
            "rules": {},
            "is_mandatory": True,
        }
    )
    _install(monkeypatch, store)
    payload = {
        "code": "salary_slip",
        "name_en": "Salary slip",
        "accepted_formats": ["pdf"],
        "max_size_mb": 4,
        "keywords": {"en": ["salary"], "ta": []},
        "required_fields": ["name"],
        "rules": {},
        "sort_order": 30,
        "is_mandatory": True,
        "is_active": True,
    }
    created = client.post(f"/admin/services/{SERVICE_ID}/documents", headers=_auth(), json=payload)
    assert created.status_code == 201
    store.uploads.append({"id": "up1", "required_document_id": DOC_ID, "application_id": APP_ID})
    detail = client.get(f"/admin/services/{SERVICE_ID}", headers=_auth())
    assert detail.status_code == 200
    photo = next(item for item in detail.json()["documents"] if item["id"] == DOC_ID)
    assert photo["code_locked"] is True
    locked = client.put(
        f"/admin/documents/{DOC_ID}",
        headers=_auth(),
        json={**payload, "code": "new_code", "name_en": "Photo", "keywords": {"en": [], "ta": []}, "required_fields": []},
    )
    assert locked.status_code == 409
    blocked = client.delete(f"/admin/documents/{DOC_ID}", headers=_auth())
    assert blocked.status_code == 409
    bad = client.post(
        f"/admin/services/{SERVICE_ID}/documents/reorder",
        headers=_auth(),
        json={"ids": [DOC_ID]},
    )
    assert bad.status_code == 422
    ok = client.post(
        f"/admin/services/{SERVICE_ID}/documents/reorder",
        headers=_auth(),
        json={"ids": [OTHER_DOC, DOC_ID, created.json()["id"]]},
    )
    assert ok.status_code == 200


def test_duplicate_rolls_back(monkeypatch: object) -> None:
    store = Store()
    _install(monkeypatch, store)
    store.fail_next_insert = True
    # First insert is the service; make the document insert fail instead.
    original = store.fail_next_insert

    def insert_row(table: str, row: dict[str, object]) -> dict[str, object]:
        if table == "services":
            created = {"id": "clone-service", **row}
            store.services.append(created)
            return created
        raise SupabaseRequestError("insert failed")

    monkeypatch.setattr("app.routers.admin_config.insert_row", insert_row)
    monkeypatch.setattr(
        "app.routers.admin_config.insert_rows",
        lambda table, rows: (_ for _ in ()).throw(SupabaseRequestError("insert failed")),
    )
    del original
    response = client.post(
        f"/admin/services/{SERVICE_ID}/duplicate",
        headers=_auth(),
        json={"new_slug": "community-certificate-copy", "new_name_en": "Copy"},
    )
    assert response.status_code == 502
    assert not any(row.get("id") == "clone-service" for row in store.services)


def test_duplicate_success(monkeypatch: object) -> None:
    store = Store()
    _install(monkeypatch, store)
    response = client.post(
        f"/admin/services/{SERVICE_ID}/duplicate",
        headers=_auth(),
        json={"new_slug": "community-certificate-copy", "new_name_en": "Copy"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["service"]["is_active"] is False
    assert body["service"]["is_verified"] is False
    assert len(body["documents"]) == 1


def test_engine_ignores_inactive_and_runs_a_different_service() -> None:
    inactive = {
        "id": "req-old",
        "code": "old_form",
        "name_en": "Old form",
        "is_mandatory": True,
        "is_active": False,
        "keywords": {"en": ["old"]},
        "required_fields": [],
        "rules": {},
        "sort_order": 1,
    }
    salary = {
        "id": "req-salary",
        "code": "salary_slip",
        "name_en": "Salary slip",
        "is_mandatory": True,
        "is_active": True,
        "keywords": {"en": ["salary", "income"]},
        "required_fields": ["name", "date"],
        "rules": {"min_blur_score": 50, "check_name_match": False},
        "sort_order": 1,
        "validity_days": 365,
    }
    upload = DocumentInput(
        document_id="up-salary",
        config=salary,
        quality_metrics={
            "width": 1200,
            "height": 1600,
            "blur_score": 400,
            "brightness_mean": 140,
            "skew_angle_degrees": 0,
            "is_probably_blank": False,
            "ocr_mean_confidence": 90,
            "ocr_word_count": 20,
        },
        ocr_text_masked="Salary income slip Name: Example 01/11/2026",
        status="processed",
    )
    results = validate_application([inactive, salary], [upload], today=date(2026, 11, 18))
    assert all(item.check_code != "missing_document" for item in results)
    assert any(item.check_code == "document_type" for item in results)
    report = build_report(
        {},
        {"name_en": "Income Certificate"},
        [inactive, salary],
        [{"id": "up-salary", "required_document_id": "req-salary", "status": "processed"}],
        results,
        datetime(2026, 11, 18, tzinfo=timezone.utc),
    )
    assert report["score"] >= 0
    assert [item["code"] for item in report["documents"]] == ["salary_slip"]


def test_stats_hide_sensitive_markers() -> None:
    profiles = [{"id": MARKER_USER, "role": "admin", "email": MARKER_EMAIL}]
    applications = [
        {
            "id": APP_ID,
            "service_id": SERVICE_ID,
            "user_id": MARKER_USER,
            "readiness_score": 90,
            "summary": {"report": {"label": "ready"}},
            "created_at": "2026-11-18T10:00:00+00:00",
            "updated_at": "2026-11-18T11:00:00+00:00",
            "ocr_text_masked": MARKER_OCR,
            "storage_path": MARKER_PATH,
            "holder_name": MARKER_NAME,
        }
    ]
    uploads = [{"id": "u1", "application_id": APP_ID, "status": "processed", "storage_path": MARKER_PATH}]
    numbers = totals(profiles, applications, uploads)
    assert numbers["users"] == 1
    assert numbers["applications_checked"] == 1
    summary = score_summary(applications)
    assert summary["average"] == 90.0
    assert summary["distribution"]["ready"] == 1
    reasons = top_failure_reasons(
        [
            {"check_code": "image_quality", "check_name": "Photo quality", "status": "fail", "message": MARKER_OCR},
            {"check_code": "image_quality", "check_name": "Photo quality", "status": "fail"},
            {"check_code": "date_validity", "check_name": "Date", "status": "warning"},
        ]
    )
    assert reasons[0]["check_code"] == "image_quality"
    assert reasons[0]["count"] == 2
    dumped = str(reasons) + str(numbers) + anonymise_user_id(MARKER_USER)
    assert MARKER_EMAIL not in dumped
    assert MARKER_NAME not in dumped
    assert MARKER_OCR not in dumped
    assert MARKER_PATH not in dumped
    assert MARKER_USER not in anonymise_user_id(MARKER_USER)
    series = activity(applications, 3, date(2026, 11, 18))
    assert series[-1]["date"] == "2026-11-18"
    assert series[-1]["count"] == 1
    assert series[0]["count"] == 0


def test_stats_endpoint_privacy(monkeypatch: object) -> None:
    store = Store()
    store.applications.append(
        {
            "id": APP_ID,
            "service_id": SERVICE_ID,
            "user_id": MARKER_USER,
            "readiness_score": 70,
            "summary": {"report": {"label": "almost_ready"}},
            "created_at": "2026-11-18T10:00:00+00:00",
            "updated_at": "2026-11-18T10:00:00+00:00",
            "email": MARKER_EMAIL,
        }
    )
    store.results.append({"check_code": "image_quality", "check_name": "Photo quality", "status": "fail", "message": MARKER_OCR})
    _install(monkeypatch, store)
    response = client.get("/admin/stats", headers=_auth())
    assert response.status_code == 200
    text = response.text
    assert MARKER_EMAIL not in text
    assert MARKER_OCR not in text
    assert MARKER_PATH not in text
    assert MARKER_USER not in text
    listed = client.get("/admin/applications", headers=_auth())
    assert listed.status_code == 200
    assert MARKER_USER not in listed.text
    assert listed.json()["items"][0]["user_label"].startswith("User #")
