"""Store, preview, replace, and delete a citizen's checklist files.

The service-role key bypasses row-level security, so every route checks that
the application's user_id is the caller. Someone else's row answers 404.
"""

from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response

from app.auth import CurrentUser, get_current_user
from app.file_checks import allowed_bytes, read_upload, storage_path
from app.supabase_client import (
    SupabaseRequestError,
    create_signed_url,
    delete_objects,
    delete_rows,
    get_rows,
    insert_row,
    update_rows,
    upload_object,
)

router = APIRouter()

MAX_DOCUMENTS = 20
SIGNED_URL_SECONDS = 300


def _missing() -> HTTPException:
    return HTTPException(status_code=404, detail="This application was not found.")


def _storage_failed() -> HTTPException:
    return HTTPException(status_code=502, detail="The file could not be saved. Please try again.")


def public_document(row: dict[str, Any]) -> dict[str, Any]:
    """Fields the browser may see. The storage path stays on the server."""
    return {
        "id": row.get("id"),
        "required_document_id": row.get("required_document_id"),
        "original_filename": row.get("original_filename"),
        "mime_type": row.get("mime_type"),
        "size_bytes": row.get("size_bytes"),
        "status": row.get("status"),
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
    }


def _owned_application(application_id: str, user_id: str) -> dict[str, Any]:
    rows = get_rows(
        "applications",
        {
            "id": f"eq.{application_id}",
            "user_id": f"eq.{user_id}",
            "select": "id,user_id,service_id",
            "limit": "1",
        },
    )
    if not rows:
        raise _missing()
    return rows[0]


def _required_document(required_document_id: str, service_id: str) -> dict[str, Any]:
    rows = get_rows(
        "required_documents",
        {
            "id": f"eq.{required_document_id}",
            "select": "id,service_id,code,accepted_formats,max_size_mb,is_active",
            "limit": "1",
        },
    )
    if not rows:
        raise HTTPException(status_code=404, detail="This checklist item was not found.")
    document = rows[0]
    if document.get("service_id") != service_id or not document.get("is_active", True):
        raise HTTPException(status_code=400, detail="This document is not part of this application.")
    return document


def _existing_upload(application_id: str, required_document_id: str) -> dict[str, Any] | None:
    rows = get_rows(
        "uploaded_documents",
        {
            "application_id": f"eq.{application_id}",
            "required_document_id": f"eq.{required_document_id}",
            "select": "id,storage_path,original_filename,mime_type,size_bytes,status,created_at",
            "limit": "1",
        },
    )
    return rows[0] if rows else None


def _owned_upload(document_id: str, user_id: str) -> dict[str, Any]:
    rows = get_rows(
        "uploaded_documents",
        {
            "id": f"eq.{document_id}",
            "user_id": f"eq.{user_id}",
            "select": "id,application_id,user_id,storage_path,mime_type,required_document_id,original_filename,size_bytes,status,created_at,updated_at",
            "limit": "1",
        },
    )
    if not rows:
        raise HTTPException(status_code=404, detail="This file was not found.")
    return rows[0]


def _restore_path(document_id: str, old_path: str) -> bool:
    """Point the row back at the previous file. False means the new file must stay."""
    try:
        restored = update_rows(
            "uploaded_documents",
            {"id": f"eq.{document_id}"},
            {"storage_path": old_path},
        )
    except SupabaseRequestError:
        return False
    return bool(restored)


def _formats(document: dict[str, Any]) -> list[str]:
    raw = document.get("accepted_formats") or []
    if not isinstance(raw, list):
        return []
    return [str(item) for item in raw]


@router.post("/applications/{application_id}/documents/{required_document_id}")
async def upload_document(
    application_id: str,
    required_document_id: str,
    user: CurrentUser = Depends(get_current_user),
    file: UploadFile | None = File(default=None),
) -> dict[str, Any]:
    """Save one checklist file, or replace the file already in that slot."""
    if file is None:
        raise HTTPException(status_code=400, detail="Choose a file to upload.")

    try:
        application = _owned_application(application_id, user.user_id)
        document = _required_document(required_document_id, str(application["service_id"]))
        existing = _existing_upload(application_id, required_document_id)
        if existing is None:
            current = get_rows(
                "uploaded_documents",
                {"application_id": f"eq.{application_id}", "select": "id"},
            )
            if len(current) >= MAX_DOCUMENTS:
                raise HTTPException(
                    status_code=400,
                    detail="This application already has the maximum of 20 documents.",
                )
        _extension, mime_type, content = await read_upload(
            file,
            allowed_bytes(int(document.get("max_size_mb") or 0)),
            _formats(document),
        )

        path = storage_path(user.user_id, application_id, str(document.get("code") or "document"), file.filename or "file")
        filename = file.filename.replace("\\", "/").split("/")[-1] if file.filename else "file"
        saved = {
            "original_filename": filename[:200],
            "mime_type": mime_type,
            "size_bytes": len(content),
            "status": "uploaded",
            "quality_metrics": {},
            "ocr_text_masked": None,
            "extracted_fields": {},
            "storage_path": path,
        }
        try:
            upload_object(path, content, mime_type)
        except SupabaseRequestError as exc:
            raise _storage_failed() from exc

        if existing is None:
            try:
                created = insert_row(
                    "uploaded_documents",
                    {
                        "application_id": application_id,
                        "required_document_id": required_document_id,
                        "user_id": user.user_id,
                        **saved,
                    },
                )
            except SupabaseRequestError as exc:
                delete_objects([path])
                raise _storage_failed() from exc
            return public_document(created)

        old_path = str(existing.get("storage_path") or "")
        try:
            updated = update_rows(
                "uploaded_documents",
                {"id": f"eq.{existing['id']}"},
                saved,
            )
        except SupabaseRequestError as exc:
            delete_objects([path])
            raise _storage_failed() from exc
        if not updated:
            delete_objects([path])
            raise _storage_failed()

        try:
            delete_rows("validation_results", {"uploaded_document_id": f"eq.{existing['id']}"})
        except SupabaseRequestError as exc:
            if _restore_path(str(existing["id"]), old_path):
                delete_objects([path])
            raise _storage_failed() from exc

        if old_path and old_path != path:
            try:
                delete_objects([old_path])
            except SupabaseRequestError as exc:
                if _restore_path(str(existing["id"]), old_path):
                    delete_objects([path])
                raise _storage_failed() from exc
        return public_document(updated[0])
    finally:
        await file.close()


@router.get("/applications/{application_id}/documents")
def list_documents(
    application_id: str,
    user: CurrentUser = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """List this citizen's files for one application."""
    _owned_application(application_id, user.user_id)
    rows = get_rows(
        "uploaded_documents",
        {
            "application_id": f"eq.{application_id}",
            "user_id": f"eq.{user.user_id}",
            "select": "id,required_document_id,original_filename,mime_type,size_bytes,status,created_at,updated_at",
        },
    )
    return [public_document(row) for row in rows]


@router.get("/documents/{document_id}/preview-url")
def preview_url(
    document_id: str,
    user: CurrentUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Return a new 5-minute link. Call this again each time the citizen presses Preview."""
    document = _owned_upload(document_id, user.user_id)
    _owned_application(str(document["application_id"]), user.user_id)
    path = str(document.get("storage_path") or "")
    try:
        url = create_signed_url(path, SIGNED_URL_SECONDS)
    except SupabaseRequestError as exc:
        raise HTTPException(status_code=502, detail="A preview link could not be created.") from exc
    return {"url": url, "mime_type": document.get("mime_type"), "expires_in": SIGNED_URL_SECONDS}


@router.delete("/documents/{document_id}", status_code=204)
def delete_document(
    document_id: str,
    user: CurrentUser = Depends(get_current_user),
) -> Response:
    """Remove one file, its check results, and its storage object."""
    document = _owned_upload(document_id, user.user_id)
    path = str(document.get("storage_path") or "")
    try:
        if path:
            delete_objects([path])
        delete_rows("validation_results", {"uploaded_document_id": f"eq.{document_id}"})
        delete_rows("uploaded_documents", {"id": f"eq.{document_id}", "user_id": f"eq.{user.user_id}"})
    except SupabaseRequestError as exc:
        raise HTTPException(status_code=502, detail="The file could not be deleted.") from exc
    return Response(status_code=204)


@router.delete("/applications/{application_id}", status_code=204)
def delete_application(
    application_id: str,
    user: CurrentUser = Depends(get_current_user),
) -> Response:
    """Remove every stored file for this application, then the application row."""
    _owned_application(application_id, user.user_id)
    rows = get_rows(
        "uploaded_documents",
        {
            "application_id": f"eq.{application_id}",
            "user_id": f"eq.{user.user_id}",
            "select": "storage_path",
        },
    )
    paths = [str(row.get("storage_path")) for row in rows if row.get("storage_path")]
    try:
        delete_objects(paths)
        delete_rows("applications", {"id": f"eq.{application_id}", "user_id": f"eq.{user.user_id}"})
    except SupabaseRequestError as exc:
        raise HTTPException(status_code=502, detail="The application could not be deleted.") from exc
    return Response(status_code=204)
