"""Upload checks that never call the real Supabase project."""

from collections.abc import Iterator

import httpx
from fastapi.testclient import TestClient

from app.config import settings
from app.file_checks import UploadTooLarge, read_limited_chunks
from app.main import app
from app.supabase_client import SupabaseRequestError, absolute_signed_url, create_signed_url
from tests.test_auth import USER_ID, _token, _use_local_tokens

client = TestClient(app)
APP_ID = "22222222-2222-2222-2222-222222222222"
REQUIRED_ID = "33333333-3333-3333-3333-333333333333"
UPLOAD_ID = "44444444-4444-4444-4444-444444444444"
SERVICE_ID = "55555555-5555-5555-5555-555555555555"


class Store:
    """The fake database and bucket used by one test."""

    def __init__(self) -> None:
        self.row: dict[str, object] | None = None
        self.objects: dict[str, bytes] = {}
        self.uploads: list[str] = []
        self.deleted_objects: list[str] = []
        self.deleted_tables: list[str] = []
        self.fail_insert = False
        self.required_service = SERVICE_ID
        self.active = True
        self.count = 0
        self.application_deleted = False
        self.validation_deleted = False
        self.deleted_matches: list[tuple[str, dict[str, str]]] = []


def _install(monkeypatch: object, store: Store) -> None:
    _use_local_tokens(monkeypatch, "citizen")

    def get_rows(table: str, params: dict[str, str]) -> list[dict[str, object]]:
        if table == "applications":
            if params.get("user_id") != f"eq.{USER_ID}" or params.get("id") != f"eq.{APP_ID}":
                return []
            return [{"id": APP_ID, "user_id": USER_ID, "service_id": SERVICE_ID}]
        if table == "required_documents":
            if params.get("id") != f"eq.{REQUIRED_ID}":
                return []
            return [
                {
                    "id": REQUIRED_ID,
                    "service_id": store.required_service,
                    "code": "photo",
                    "accepted_formats": ["jpg", "jpeg", "png", "pdf"],
                    "max_size_mb": 5,
                    "is_active": store.active,
                }
            ]
        if table != "uploaded_documents":
            return []
        if "required_document_id" in params:
            return [store.row] if store.row else []
        if params.get("select") == "id":
            return [{"id": f"count-{index}"} for index in range(store.count)]
        if params.get("select") == "storage_path":
            if store.row and store.row.get("storage_path"):
                return [{"storage_path": store.row["storage_path"]}]
            return []
        if "id" in params and "application_id" not in params:
            if store.row and params.get("id") == f"eq.{store.row['id']}" and params.get("user_id") == f"eq.{USER_ID}":
                return [store.row]
            return []
        return [store.row] if store.row else []

    def upload_object(path: str, content_bytes: bytes, content_type: str) -> None:
        store.uploads.append(path)
        store.objects[path] = content_bytes
        del content_type

    def delete_objects(paths: list[str]) -> None:
        store.deleted_objects.extend(paths)
        for path in paths:
            store.objects.pop(path, None)

    def insert_row(table: str, row: dict[str, object]) -> dict[str, object]:
        del table
        if store.fail_insert:
            raise SupabaseRequestError("insert failed")
        created = {
            "id": UPLOAD_ID,
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z",
            **row,
        }
        store.row = created
        return created

    def update_rows(table: str, match: dict[str, str], values: dict[str, object]) -> list[dict[str, object]]:
        del table, match
        if store.row is None:
            return []
        store.row.update(values)
        store.row["updated_at"] = "2026-01-02T00:00:00Z"
        return [dict(store.row)]

    def delete_rows(table: str, match: dict[str, str]) -> None:
        store.deleted_matches.append((table, dict(match)))
        store.deleted_tables.append(table)
        if table == "validation_results":
            store.validation_deleted = True
        if table == "uploaded_documents":
            store.row = None
        if table == "applications":
            store.application_deleted = True

    def signed(path: str, expires_in: int = 300) -> str:
        del path, expires_in
        return "https://files.example/signed/preview"

    monkeypatch.setattr("app.routers.documents.get_rows", get_rows)
    monkeypatch.setattr("app.routers.documents.upload_object", upload_object)
    monkeypatch.setattr("app.routers.documents.delete_objects", delete_objects)
    monkeypatch.setattr("app.routers.documents.insert_row", insert_row)
    monkeypatch.setattr("app.routers.documents.update_rows", update_rows)
    monkeypatch.setattr("app.routers.documents.delete_rows", delete_rows)
    monkeypatch.setattr("app.routers.documents.create_signed_url", signed)


def _cleared_shared_results(store: Store) -> bool:
    return any(
        table == "validation_results" and match.get("uploaded_document_id") == "is.null" and match.get("application_id") == f"eq.{APP_ID}"
        for table, match in store.deleted_matches
    )


def _auth() -> dict[str, str]:
    return {"Authorization": f"Bearer {_token()}"}


def _send(name: str, content: bytes, content_type: str, store: Store | None = None) -> httpx.Response:
    del store
    return client.post(
        f"/applications/{APP_ID}/documents/{REQUIRED_ID}",
        headers=_auth(),
        files={"file": (name, content, content_type)},
    )


def test_upload_without_token_is_401() -> None:
    response = client.post(f"/applications/{APP_ID}/documents/{REQUIRED_ID}")
    assert response.status_code == 401


def test_preview_without_token_is_401() -> None:
    response = client.get(f"/documents/{UPLOAD_ID}/preview-url")
    assert response.status_code == 401


def test_delete_document_without_token_is_401() -> None:
    response = client.delete(f"/documents/{UPLOAD_ID}")
    assert response.status_code == 401


def test_delete_application_without_token_is_401() -> None:
    response = client.delete(f"/applications/{APP_ID}")
    assert response.status_code == 401


def test_other_users_application_is_404(monkeypatch: object) -> None:
    _install(monkeypatch, Store())
    token = _token({"sub": "99999999-9999-9999-9999-999999999999"})
    response = client.post(
        f"/applications/{APP_ID}/documents/{REQUIRED_ID}",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("a.jpg", b"\xff\xd8\xff\x00", "image/jpeg")},
    )
    assert response.status_code == 404


def test_document_from_another_service_is_400(monkeypatch: object) -> None:
    store = Store()
    store.required_service = "other-service"
    _install(monkeypatch, store)
    response = _send("a.jpg", b"\xff\xd8\xff\x00", "image/jpeg")
    assert response.status_code == 400


def test_wrong_extension_is_415(monkeypatch: object) -> None:
    _install(monkeypatch, Store())
    response = _send("notes.txt", b"hello", "text/plain")
    assert response.status_code == 415


def test_renamed_text_file_is_415(monkeypatch: object) -> None:
    _install(monkeypatch, Store())
    response = _send("fake.pdf", b"this is not a pdf", "application/pdf")
    assert response.status_code == 415


def test_empty_file_is_400(monkeypatch: object) -> None:
    _install(monkeypatch, Store())
    response = _send("empty.pdf", b"", "application/pdf")
    assert response.status_code == 400


def test_oversized_file_is_413_and_stops_early(monkeypatch: object) -> None:
    store = Store()
    _install(monkeypatch, store)
    monkeypatch.setattr(settings, "MAX_UPLOAD_MB", 0)
    response = _send("big.jpg", b"\xff\xd8\xff" + (b"x" * 50), "image/jpeg")
    assert response.status_code == 413
    assert store.uploads == []

    seen = {"chunks": 0}

    def chunks() -> Iterator[bytes]:
        for _ in range(5):
            seen["chunks"] += 1
            yield b"x" * 100

    try:
        read_limited_chunks(chunks(), 150)
        raised = False
    except UploadTooLarge:
        raised = True
    assert raised
    assert seen["chunks"] == 2


def test_valid_jpg_png_and_pdf_hide_storage_path(monkeypatch: object) -> None:
    samples = [
        ("photo.jpg", b"\xff\xd8\xff\x00", "image/jpeg"),
        ("photo.png", b"\x89PNG\r\n\x1a\nrest", "image/png"),
        ("photo.pdf", b"%PDF-1.4\n", "application/pdf"),
    ]
    for name, content, mime in samples:
        store = Store()
        _install(monkeypatch, store)
        response = _send(name, content, mime)
        body = response.json()
        assert response.status_code == 200
        assert body["status"] == "uploaded"
        assert body["mime_type"] == mime
        assert "storage_path" not in body
        text = response.text
        assert "eyJ" not in text
        assert "sb_secret" not in text
        assert "service_role" not in text


def test_path_traversal_filename_is_sanitized(monkeypatch: object) -> None:
    store = Store()
    _install(monkeypatch, store)
    response = _send("../../x.pdf", b"%PDF-1.4\n", "application/pdf")
    assert response.status_code == 200
    path = store.uploads[0]
    assert path.startswith(f"{USER_ID}/{APP_ID}/photo-")
    assert ".." not in path
    assert path.endswith("-x.pdf")


def test_replace_uploads_new_and_removes_old(monkeypatch: object) -> None:
    store = Store()
    store.row = {
        "id": UPLOAD_ID,
        "application_id": APP_ID,
        "required_document_id": REQUIRED_ID,
        "user_id": USER_ID,
        "storage_path": f"{USER_ID}/{APP_ID}/photo-old-old.jpg",
        "original_filename": "old.jpg",
        "mime_type": "image/jpeg",
        "size_bytes": 4,
        "status": "uploaded",
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
    }
    _install(monkeypatch, store)
    response = _send("new.png", b"\x89PNG\r\n\x1a\nrest", "image/png")
    assert response.status_code == 200
    assert store.uploads
    assert store.deleted_objects == [f"{USER_ID}/{APP_ID}/photo-old-old.jpg"]
    assert store.validation_deleted
    assert _cleared_shared_results(store)
    assert response.json()["original_filename"] == "new.png"
    assert "storage_path" not in response.json()
    assert store.row is not None
    assert store.row["status"] == "uploaded"
    assert store.row["quality_metrics"] == {}
    assert store.row["ocr_text_masked"] is None


def test_failed_insert_removes_the_new_object(monkeypatch: object) -> None:
    store = Store()
    store.fail_insert = True
    _install(monkeypatch, store)
    response = _send("photo.jpg", b"\xff\xd8\xff\x00", "image/jpeg")
    assert response.status_code == 502
    assert store.uploads
    assert store.deleted_objects == store.uploads
    assert store.objects == {}


def test_preview_url_is_only_for_the_owner(monkeypatch: object) -> None:
    store = Store()
    store.row = {
        "id": UPLOAD_ID,
        "application_id": APP_ID,
        "user_id": USER_ID,
        "storage_path": f"{USER_ID}/{APP_ID}/photo-aaaaaaaa-a.jpg",
        "mime_type": "image/jpeg",
    }
    _install(monkeypatch, store)
    owned = client.get(f"/documents/{UPLOAD_ID}/preview-url", headers=_auth())
    assert owned.status_code == 200
    assert owned.json()["url"] == "https://files.example/signed/preview"
    assert owned.json()["expires_in"] == 300
    stranger = _token({"sub": "99999999-9999-9999-9999-999999999999"})
    denied = client.get(
        f"/documents/{UPLOAD_ID}/preview-url",
        headers={"Authorization": f"Bearer {stranger}"},
    )
    assert denied.status_code == 404


def test_delete_document_removes_object_and_row(monkeypatch: object) -> None:
    store = Store()
    path = f"{USER_ID}/{APP_ID}/photo-aaaaaaaa-a.jpg"
    store.row = {"id": UPLOAD_ID, "application_id": APP_ID, "user_id": USER_ID, "storage_path": path}
    store.objects[path] = b"\xff\xd8\xff"
    _install(monkeypatch, store)
    response = client.delete(f"/documents/{UPLOAD_ID}", headers=_auth())
    assert response.status_code == 204
    assert response.content == b""
    assert response.headers.get("content-length") == "0"
    assert path in store.deleted_objects
    assert store.row is None
    assert _cleared_shared_results(store)


def test_delete_application_removes_objects_then_row(monkeypatch: object) -> None:
    store = Store()
    path = f"{USER_ID}/{APP_ID}/photo-aaaaaaaa-a.jpg"
    store.row = {"id": UPLOAD_ID, "storage_path": path, "user_id": USER_ID}
    _install(monkeypatch, store)
    response = client.delete(f"/applications/{APP_ID}", headers=_auth())
    assert response.status_code == 204
    assert store.deleted_objects == [path]
    assert store.application_deleted
    assert store.deleted_tables[-1] == "applications"


def test_signed_url_accepts_both_response_keys(monkeypatch: object) -> None:
    monkeypatch.setattr(settings, "SUPABASE_URL", "https://project.example")
    monkeypatch.setattr(settings, "SUPABASE_SERVICE_ROLE_KEY", "test-key")
    seen = {"key": "signedURL"}

    def fake_request(method: str, url: str, **kwargs: object) -> object:
        del method, url, kwargs

        class Response:
            status_code = 200
            text = ""

            def json(self) -> dict[str, str]:
                return {seen["key"]: "/object/sign/documents/a?token=1"}

        return Response()

    monkeypatch.setattr("app.supabase_client.httpx.request", fake_request)
    first = create_signed_url("user/app/a.pdf")
    seen["key"] = "signedUrl"
    second = create_signed_url("user/app/a.pdf")
    assert first == second
    assert first == "https://project.example/storage/v1/object/sign/documents/a?token=1"
    assert absolute_signed_url("https://project.example", "https://cdn.example/file") == "https://cdn.example/file"
