"""Store, preview, replace, delete, and read a citizen's checklist files.

The service-role key bypasses row-level security, so every route checks that
the application's user_id is the caller. Someone else's row answers 404.
OCR text is masked before it is saved and is never written to the log.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse, Response

from app.ai.hygiene import clear_ai_advice
from app.auth import CurrentUser, get_current_user
from app.errors import error_response
from app.limits.ratelimit import require_process_user, require_upload_user
from app.request_context import get_request_id
from app.report.hygiene import clear_stale_report
from app.file_checks import allowed_bytes, read_upload, storage_path
from app.processing.loader import DocumentUnreadableError
from app.processing.masking import mask_sensitive
from app.processing.pipeline import process_document
from app.supabase_client import (
    SupabaseRequestError,
    create_signed_url,
    delete_objects,
    delete_rows,
    download_object,
    get_rows,
    insert_row,
    update_rows,
    upload_object,
)

logger = logging.getLogger(__name__)

router = APIRouter()

MAX_DOCUMENTS = 20
SIGNED_URL_SECONDS = 300


def _clear_shared_checks(application_id: str) -> None:
    """Drop checklist-wide results. One file change makes them out of date."""
    if not application_id:
        return
    delete_rows(
        "validation_results",
        {"application_id": f"eq.{application_id}", "uploaded_document_id": "is.null"},
    )


def _clear_ai_advice(application_id: str) -> None:
    """Forget simple explanations after the files or the checks change."""
    try:
        clear_ai_advice(application_id, reader=get_rows, writer=update_rows)
    except Exception as exc:
        logger.info("ai advice clear failed error_type=%s", type(exc).__name__)


def _clear_stale_report(application_id: str) -> None:
    """Drop the saved score after a file is uploaded, replaced, deleted, or re-read."""
    try:
        clear_stale_report(application_id, reader=get_rows, writer=update_rows)
    except Exception as exc:
        logger.info("report clear failed error_type=%s", type(exc).__name__)


def _after_document_change(application_id: str) -> None:
    """AI advice and the printable report both go stale when the files change."""
    _clear_ai_advice(application_id)
    _clear_stale_report(application_id)


def _clear_saved_checks(application_id: str, document_id: str) -> None:
    """Drop this file's results and the checklist-wide results after a new read."""
    try:
        delete_rows("validation_results", {"uploaded_document_id": f"eq.{document_id}"})
        _clear_shared_checks(application_id)
    except SupabaseRequestError:
        # The new reading is already saved. The next check replaces old rows.
        return


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
        "quality_metrics": row.get("quality_metrics") or {},
        "ocr_text_masked": row.get("ocr_text_masked"),
        "extracted_fields": row.get("extracted_fields") if isinstance(row.get("extracted_fields"), dict) else {},
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
            "select": "id,application_id,user_id,storage_path,mime_type,required_document_id,original_filename,size_bytes,status,quality_metrics,ocr_text_masked,created_at,updated_at",
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
    user: CurrentUser = Depends(require_upload_user),
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
            _after_document_change(application_id)
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
            _clear_shared_checks(application_id)
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
        _after_document_change(application_id)
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
    _after_document_change(str(document.get("application_id") or ""))
    path = str(document.get("storage_path") or "")
    try:
        if path:
            delete_objects([path])
        delete_rows("validation_results", {"uploaded_document_id": f"eq.{document_id}"})
        _clear_shared_checks(str(document.get("application_id") or ""))
        delete_rows("uploaded_documents", {"id": f"eq.{document_id}", "user_id": f"eq.{user.user_id}"})
    except SupabaseRequestError as exc:
        raise HTTPException(status_code=502, detail="The file could not be deleted.") from exc
    # A length is required so the browser finishes the empty response and the page can clear the slot.
    return Response(status_code=204, headers={"content-length": "0"})


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
    return Response(status_code=204, headers={"content-length": "0"})


def _result_body(row: dict[str, Any]) -> dict[str, Any]:
    """Fields the browser may see after a read. The storage path stays on the server."""
    metrics = row.get("quality_metrics") or {}
    if not isinstance(metrics, dict):
        metrics = {}
    text = row.get("ocr_text_masked")
    if text is not None and not isinstance(text, str):
        text = None
    return {
        "id": row.get("id"),
        "status": row.get("status"),
        "quality_metrics": metrics,
        "ocr_text_masked": text,
        "updated_at": row.get("updated_at"),
    }


def _fresh_processing(row: dict[str, Any]) -> bool:
    """True when a read started less than two minutes ago and should not be restarted."""
    if row.get("status") != "processing":
        return False
    raw = str(row.get("updated_at") or "")
    if not raw:
        return False
    try:
        stamp = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return False
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - stamp < timedelta(minutes=2)


def _friendly_error(exc: Exception) -> str:
    """A short message for the citizen. It never includes the words that were read."""
    if isinstance(exc, DocumentUnreadableError):
        return str(exc)[:180]
    if isinstance(exc, SupabaseRequestError):
        return "The stored file could not be read. Please try again."
    return "We could not read this document. Please try a clearer photo."


def _save_failure(row: dict[str, Any], message: str) -> dict[str, Any]:
    failed = {
        "status": "failed",
        "quality_metrics": {"error": message},
        "ocr_text_masked": None,
        "extracted_fields": {},
    }
    try:
        updated = update_rows("uploaded_documents", {"id": f"eq.{row['id']}"}, failed)
    except SupabaseRequestError:
        updated = []
    if updated:
        return updated[0]
    merged = dict(row)
    merged.update(failed)
    return merged


def _download_and_process(path: str, mime_type: str) -> dict[str, object]:
    """Download and read away from the request loop. The path is not logged."""
    content = download_object(path)
    return process_document(content, mime_type)


@router.post("/documents/{document_id}/process")
async def process_upload(
    document_id: str,
    user: CurrentUser = Depends(require_process_user),
) -> JSONResponse:
    """Read one of the caller's files and store masked text plus quality numbers."""
    row = _owned_upload(document_id, user.user_id)
    if _fresh_processing(row):
        raise HTTPException(status_code=409, detail="Already processing")

    path = str(row.get("storage_path") or "")
    mime_type = str(row.get("mime_type") or "")
    try:
        marked = update_rows("uploaded_documents", {"id": f"eq.{row['id']}"}, {"status": "processing"})
    except SupabaseRequestError as exc:
        raise HTTPException(status_code=502, detail="The file could not be read. Please try again.") from exc
    if marked:
        row = marked[0]
    if not path:
        message = "The stored file could not be found."
        failed = _save_failure(row, message)
        _after_document_change(str(row.get("application_id") or ""))
        body = _result_body(failed)
        return error_response(422, message, extra=body)

    started = datetime.now(timezone.utc)
    try:
        outcome = await run_in_threadpool(_download_and_process, path, mime_type)
    except Exception as exc:
        message = _friendly_error(exc)
        failed = _save_failure(row, message)
        _clear_saved_checks(str(row.get("application_id") or ""), document_id)
        _after_document_change(str(row.get("application_id") or ""))
        logger.info("ocr failed request_id=%s error_type=%s", get_request_id(), type(exc).__name__)
        body = _result_body(failed)
        return error_response(422, message, extra=body)

    raw_text = outcome.get("ocr_text_masked")
    masked_text, _count = mask_sensitive(raw_text if isinstance(raw_text, str) else "")
    if len(masked_text) > 20000:
        masked_text = masked_text[:20000]
    metrics = outcome.get("quality_metrics")
    if not isinstance(metrics, dict):
        metrics = {}
    try:
        updated = update_rows(
            "uploaded_documents",
            {"id": f"eq.{row['id']}"},
            {
                "status": "processed",
                "quality_metrics": metrics,
                "ocr_text_masked": masked_text,
                "extracted_fields": {},
            },
        )
    except SupabaseRequestError as exc:
        message = "The reading finished but could not be saved. Please try again."
        failed = _save_failure(row, message)
        _after_document_change(str(row.get("application_id") or ""))
        body = _result_body(failed)
        return error_response(422, message, extra=body)

    saved = updated[0] if updated else {
        **row,
        "status": "processed",
        "quality_metrics": metrics,
        "ocr_text_masked": masked_text,
    }
    _clear_saved_checks(str(saved.get("application_id") or row.get("application_id") or ""), document_id)
    _after_document_change(str(saved.get("application_id") or row.get("application_id") or ""))
    elapsed_ms = int((datetime.now(timezone.utc) - started).total_seconds() * 1000)
    logger.info("ocr finished request_id=%s status=processed ms=%s", get_request_id(), elapsed_ms)
    return JSONResponse(status_code=200, content=_result_body(saved))


@router.get("/documents/{document_id}/result")
def document_result(
    document_id: str,
    user: CurrentUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Return the saved reading for a file the caller owns."""
    row = _owned_upload(document_id, user.user_id)
    return _result_body(row)
