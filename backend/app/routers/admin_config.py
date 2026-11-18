"""Admin CRUD for services and required documents.

Every route uses require_admin. The role comes from the profiles table.
Responses never include files, OCR text, storage paths, or emails.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app.admin.clone import build_clone_payload
from app.admin.config_validation import (
    RequiredDocumentInput,
    ServiceInput,
    document_row,
    parse_model,
    service_row,
)
from app.auth import CurrentUser, require_admin
from app.supabase_client import (
    SupabaseRequestError,
    count_rows,
    delete_rows,
    get_rows,
    insert_row,
    insert_rows,
    update_rows,
)

router = APIRouter()

_SERVICE_PUBLIC = "id,slug,name_en,name_ta,description,is_active,is_verified,created_at,updated_at"
_DOC_PUBLIC = (
    "id,service_id,code,name_en,name_ta,description,is_mandatory,accepted_formats,"
    "max_size_mb,validity_days,keywords,required_fields,rules,sort_order,is_active,created_at,updated_at"
)


def _http_errors(errors: list[dict[str, str]]) -> HTTPException:
    return HTTPException(status_code=422, detail=errors)


def _conflict(message: str) -> HTTPException:
    return HTTPException(status_code=409, detail=message)


def _missing(kind: str = "service") -> HTTPException:
    return HTTPException(status_code=404, detail=f"This {kind} was not found.")


def _is_duplicate(exc: SupabaseRequestError) -> bool:
    text = str(exc).lower()
    return "409" in text or "duplicate" in text or "unique" in text


def _load_service(service_id: str) -> dict[str, Any]:
    rows = get_rows(
        "services",
        {"id": f"eq.{service_id}", "select": _SERVICE_PUBLIC, "limit": "1"},
    )
    if not rows:
        raise _missing("service")
    return rows[0]


def _application_count(service_id: str) -> int:
    return count_rows("applications", {"service_id": f"eq.{service_id}"})


def _upload_count_for_document(required_document_id: str) -> int:
    return count_rows("uploaded_documents", {"required_document_id": f"eq.{required_document_id}"})


def _document_counts() -> dict[str, dict[str, int]]:
    rows = get_rows("required_documents", {"select": "service_id,is_active", "limit": "5000"})
    counts: dict[str, dict[str, int]] = {}
    for row in rows:
        service_id = str(row.get("service_id") or "")
        bucket = counts.setdefault(service_id, {"active": 0, "total": 0})
        bucket["total"] += 1
        if row.get("is_active") is True:
            bucket["active"] += 1
    return counts


def _application_counts() -> dict[str, int]:
    rows = get_rows("applications", {"select": "service_id", "limit": "5000"})
    counts: dict[str, int] = {}
    for row in rows:
        service_id = str(row.get("service_id") or "")
        counts[service_id] = counts.get(service_id, 0) + 1
    return counts


@router.get("/admin/services")
def list_services(_: CurrentUser = Depends(require_admin)) -> dict[str, Any]:
    services = get_rows("services", {"select": _SERVICE_PUBLIC, "order": "name_en.asc"})
    docs = _document_counts()
    apps = _application_counts()
    items = []
    for service in services:
        service_id = str(service.get("id") or "")
        counts = docs.get(service_id, {"active": 0, "total": 0})
        items.append(
            {
                **service,
                "documents_active": counts["active"],
                "documents_total": counts["total"],
                "applications": apps.get(service_id, 0),
            }
        )
    return {"items": items}


@router.post("/admin/services", status_code=201)
def create_service(body: dict[str, Any], _: CurrentUser = Depends(require_admin)) -> dict[str, Any]:
    parsed, errors = parse_model(ServiceInput, body)
    if parsed is None:
        raise _http_errors(errors)
    payload = service_row(parsed)
    try:
        created = insert_row("services", payload)
    except SupabaseRequestError as exc:
        if _is_duplicate(exc):
            raise _conflict("That slug is already in use.") from exc
        raise HTTPException(status_code=502, detail="The service could not be saved.") from exc
    return created


@router.get("/admin/services/{service_id}")
def read_service(service_id: str, _: CurrentUser = Depends(require_admin)) -> dict[str, Any]:
    service = _load_service(service_id)
    documents = get_rows(
        "required_documents",
        {
            "service_id": f"eq.{service_id}",
            "select": _DOC_PUBLIC,
            "order": "sort_order.asc",
        },
    )
    upload_rows = get_rows(
        "uploaded_documents",
        {"select": "required_document_id", "limit": "5000"},
    )
    upload_counts: dict[str, int] = {}
    for row in upload_rows:
        doc_id = str(row.get("required_document_id") or "")
        upload_counts[doc_id] = upload_counts.get(doc_id, 0) + 1
    safe_docs = []
    for document in documents:
        doc_id = str(document.get("id") or "")
        uploads = upload_counts.get(doc_id, 0)
        safe_docs.append({**document, "uploads": uploads, "code_locked": uploads > 0})
    return {
        "service": {**service, "applications": _application_count(service_id)},
        "documents": safe_docs,
    }


@router.put("/admin/services/{service_id}")
def update_service(service_id: str, body: dict[str, Any], _: CurrentUser = Depends(require_admin)) -> dict[str, Any]:
    current = _load_service(service_id)
    parsed, errors = parse_model(ServiceInput, body)
    if parsed is None:
        raise _http_errors(errors)
    payload = service_row(parsed)
    if payload["slug"] != current.get("slug") and _application_count(service_id) > 0:
        raise _conflict("slug is locked once applications exist")
    try:
        updated = update_rows("services", {"id": f"eq.{service_id}"}, payload)
    except SupabaseRequestError as exc:
        if _is_duplicate(exc):
            raise _conflict("That slug is already in use.") from exc
        raise HTTPException(status_code=502, detail="The service could not be saved.") from exc
    if not updated:
        raise _missing("service")
    return updated[0]


@router.post("/admin/services/{service_id}/duplicate", status_code=201)
def duplicate_service(service_id: str, body: dict[str, Any], _: CurrentUser = Depends(require_admin)) -> dict[str, Any]:
    current = _load_service(service_id)
    parsed, errors = parse_model(
        ServiceInput,
        {
            "slug": body.get("new_slug"),
            "name_en": body.get("new_name_en"),
            "name_ta": current.get("name_ta"),
            "description": current.get("description"),
            "is_active": False,
            "is_verified": False,
        },
    )
    if parsed is None:
        raise _http_errors(errors)
    documents = get_rows(
        "required_documents",
        {"service_id": f"eq.{service_id}", "select": _DOC_PUBLIC, "order": "sort_order.asc"},
    )
    service_payload, doc_payloads = build_clone_payload(current, documents, parsed.slug, parsed.name_en)
    created_id = None
    try:
        created = insert_row("services", service_payload)
        created_id = str(created.get("id") or "")
        rows = [{**item, "service_id": created_id} for item in doc_payloads]
        saved_docs = insert_rows("required_documents", rows) if rows else []
    except SupabaseRequestError as exc:
        if created_id:
            try:
                delete_rows("services", {"id": f"eq.{created_id}"})
            except SupabaseRequestError:
                pass
        if _is_duplicate(exc):
            raise _conflict("That slug is already in use.") from exc
        raise HTTPException(status_code=502, detail="The copy could not be saved.") from exc
    return {"service": created, "documents": saved_docs}


@router.delete("/admin/services/{service_id}", status_code=204)
def delete_service(service_id: str, _: CurrentUser = Depends(require_admin)) -> None:
    _load_service(service_id)
    if _application_count(service_id) > 0:
        raise _conflict("This service has been used – deactivate it instead")
    try:
        delete_rows("services", {"id": f"eq.{service_id}"})
    except SupabaseRequestError as exc:
        raise HTTPException(status_code=502, detail="The service could not be deleted.") from exc


@router.post("/admin/services/{service_id}/documents", status_code=201)
def create_document(service_id: str, body: dict[str, Any], _: CurrentUser = Depends(require_admin)) -> dict[str, Any]:
    _load_service(service_id)
    parsed, errors = parse_model(RequiredDocumentInput, body)
    if parsed is None:
        raise _http_errors(errors)
    payload = {"service_id": service_id, **document_row(parsed)}
    try:
        return insert_row("required_documents", payload)
    except SupabaseRequestError as exc:
        if _is_duplicate(exc):
            raise _conflict("That document code is already used on this service.") from exc
        raise HTTPException(status_code=502, detail="The document could not be saved.") from exc


def _load_document(required_document_id: str) -> dict[str, Any]:
    rows = get_rows(
        "required_documents",
        {"id": f"eq.{required_document_id}", "select": _DOC_PUBLIC, "limit": "1"},
    )
    if not rows:
        raise _missing("document")
    return rows[0]


@router.put("/admin/documents/{required_document_id}")
def update_document(
    required_document_id: str,
    body: dict[str, Any],
    _: CurrentUser = Depends(require_admin),
) -> dict[str, Any]:
    current = _load_document(required_document_id)
    parsed, errors = parse_model(RequiredDocumentInput, body)
    if parsed is None:
        raise _http_errors(errors)
    payload = document_row(parsed)
    if payload["code"] != current.get("code") and _upload_count_for_document(required_document_id) > 0:
        raise _conflict("code is locked once documents have been uploaded")
    try:
        updated = update_rows("required_documents", {"id": f"eq.{required_document_id}"}, payload)
    except SupabaseRequestError as exc:
        if _is_duplicate(exc):
            raise _conflict("That document code is already used on this service.") from exc
        raise HTTPException(status_code=502, detail="The document could not be saved.") from exc
    if not updated:
        raise _missing("document")
    return updated[0]


@router.delete("/admin/documents/{required_document_id}", status_code=204)
def delete_document(required_document_id: str, _: CurrentUser = Depends(require_admin)) -> None:
    _load_document(required_document_id)
    if _upload_count_for_document(required_document_id) > 0:
        raise _conflict("Documents have been uploaded for this item – deactivate it instead")
    try:
        delete_rows("required_documents", {"id": f"eq.{required_document_id}"})
    except SupabaseRequestError as exc:
        raise HTTPException(status_code=502, detail="The document could not be deleted.") from exc


@router.post("/admin/services/{service_id}/documents/reorder")
def reorder_documents(service_id: str, body: dict[str, Any], _: CurrentUser = Depends(require_admin)) -> dict[str, Any]:
    _load_service(service_id)
    ids = body.get("ids")
    if not isinstance(ids, list) or not ids or not all(isinstance(item, str) and item for item in ids):
        raise _http_errors([{"field": "ids", "message": "Send every document id for this service, in the new order."}])
    existing = get_rows(
        "required_documents",
        {"service_id": f"eq.{service_id}", "select": "id"},
    )
    existing_ids = {str(row.get("id") or "") for row in existing}
    sent = list(ids)
    if set(sent) != existing_ids or len(sent) != len(existing_ids):
        raise _http_errors([{"field": "ids", "message": "The list must include every document for this service, and only those documents."}])
    updated = []
    for index, document_id in enumerate(sent, start=1):
        rows = update_rows(
            "required_documents",
            {"id": f"eq.{document_id}", "service_id": f"eq.{service_id}"},
            {"sort_order": index * 10},
        )
        if rows:
            updated.extend(rows)
    return {"items": updated}
