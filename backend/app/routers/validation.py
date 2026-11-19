"""Run and read checklist checks.

The service-role key bypasses row-level security, so every route checks that
the application's user_id is the caller. Someone else's row answers 404.
Responses never include OCR text, names, or full ID numbers.
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app.ai.hygiene import clear_ai_advice
from app.auth import CurrentUser, get_current_user
from app.limits.ratelimit import require_validate_report_user
from app.request_context import get_request_id
from app.supabase_client import SupabaseRequestError, delete_rows, get_rows, insert_rows, update_rows
from app.validation.engine import validate_application
from app.validation.models import DocumentInput, Result

logger = logging.getLogger(__name__)

router = APIRouter()


def _missing() -> HTTPException:
    return HTTPException(status_code=404, detail="This application was not found.")


def _owned_application(application_id: str, user_id: str) -> dict[str, Any]:
    rows = get_rows(
        "applications",
        {
            "id": f"eq.{application_id}",
            "user_id": f"eq.{user_id}",
            "select": "id,user_id,service_id,status,readiness_score,summary",
            "limit": "1",
        },
    )
    if not rows:
        raise _missing()
    return rows[0]


def _public_result(row: dict[str, Any]) -> dict[str, Any]:
    """Fields the browser may see. Storage paths and OCR text are not here."""
    details = row.get("details") if isinstance(row.get("details"), dict) else {}
    return {
        "id": row.get("id"),
        "application_id": row.get("application_id"),
        "uploaded_document_id": row.get("uploaded_document_id"),
        "check_code": row.get("check_code"),
        "check_name": row.get("check_name"),
        "status": row.get("status"),
        "message": row.get("message"),
        "fix_suggestion": row.get("fix_suggestion"),
        "details": details,
        "created_at": row.get("created_at"),
    }


def _summary(rows: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "pass": sum(1 for row in rows if row.get("status") == "pass"),
        "warning": sum(1 for row in rows if row.get("status") == "warning"),
        "fail": sum(1 for row in rows if row.get("status") == "fail"),
    }


def _load_inputs(application: dict[str, Any], user_id: str) -> tuple[list[dict[str, Any]], list[DocumentInput]]:
    required = get_rows(
        "required_documents",
        {
            "service_id": f"eq.{application['service_id']}",
            "is_active": "eq.true",
            "select": "id,code,name_en,name_ta,is_mandatory,is_active,keywords,required_fields,rules,validity_days,sort_order",
            "order": "sort_order.asc",
        },
    )
    uploads = get_rows(
        "uploaded_documents",
        {
            "application_id": f"eq.{application['id']}",
            "user_id": f"eq.{user_id}",
            "select": "id,required_document_id,status,quality_metrics,ocr_text_masked,extracted_fields",
        },
    )
    by_id = {str(row.get("id")): row for row in required}
    documents: list[DocumentInput] = []
    for upload in uploads:
        config = by_id.get(str(upload.get("required_document_id")))
        if config is None:
            continue
        metrics = upload.get("quality_metrics")
        text = upload.get("ocr_text_masked")
        extracted = upload.get("extracted_fields")
        documents.append(
            DocumentInput(
                document_id=str(upload.get("id") or ""),
                config=config,
                quality_metrics=metrics if isinstance(metrics, dict) else {},
                ocr_text_masked=text if isinstance(text, str) else "",
                status=str(upload.get("status") or ""),
                extracted_fields=extracted if isinstance(extracted, dict) else {},
            )
        )
    return required, documents


def _store_results(application_id: str, results: list[Result]) -> list[dict[str, Any]]:
    """Insert the new rows first. Old rows are removed only after that succeeds."""
    payload = [
        {
            "application_id": application_id,
            "uploaded_document_id": result.uploaded_document_id,
            "check_code": result.check_code,
            "check_name": result.check_name,
            "status": result.status,
            "message": result.message,
            "fix_suggestion": result.fix_suggestion,
            "details": result.details,
        }
        for result in results
    ]
    try:
        inserted = insert_rows("validation_results", payload)
    except SupabaseRequestError as exc:
        raise HTTPException(status_code=502, detail="The checks could not be saved. Please try again.") from exc
    if len(inserted) != len(payload):
        raise HTTPException(status_code=502, detail="The checks could not be saved. Please try again.")
    try:
        if inserted:
            kept = ",".join(str(row.get("id")) for row in inserted if row.get("id"))
            delete_rows(
                "validation_results",
                {"application_id": f"eq.{application_id}", "id": f"not.in.({kept})"},
            )
        else:
            delete_rows("validation_results", {"application_id": f"eq.{application_id}"})
    except SupabaseRequestError as exc:
        raise HTTPException(status_code=502, detail="The previous checks could not be replaced. Please try again.") from exc
    return inserted


def run_and_store_validation(application_id: str, user_id: str) -> dict[str, Any]:
    """Run the checklist engine and replace saved rows. Used by validate and report."""
    application = _owned_application(application_id, user_id)
    required, documents = _load_inputs(application, user_id)
    results = validate_application(required, documents)
    saved = _store_results(application_id, results)
    try:
        clear_ai_advice(application_id, reader=get_rows, writer=update_rows)
    except Exception as exc:
        logger.info("ai advice clear failed error_type=%s", type(exc).__name__)
    public = [_public_result(row) for row in saved]
    logger.info(
        "validation finished request_id=%s pass=%s warning=%s fail=%s",
        get_request_id(),
        sum(1 for row in public if row.get("status") == "pass"),
        sum(1 for row in public if row.get("status") == "warning"),
        sum(1 for row in public if row.get("status") == "fail"),
    )
    return {
        "application": application,
        "required": required,
        "uploads": documents,
        "results": saved,
        "public": public,
    }


@router.post("/applications/{application_id}/validate")
def validate(application_id: str, user: CurrentUser = Depends(require_validate_report_user)) -> dict[str, Any]:
    """Replace this application's check results. Does not score the application."""
    payload = run_and_store_validation(application_id, user.user_id)
    return {
        "application_id": application_id,
        "results": payload["public"],
        "summary": _summary(payload["public"]),
    }


@router.get("/applications/{application_id}/validation")
def saved_validation(application_id: str, user: CurrentUser = Depends(get_current_user)) -> dict[str, Any]:
    """Return the saved checks for an application the caller owns."""
    _owned_application(application_id, user.user_id)
    rows = get_rows(
        "validation_results",
        {
            "application_id": f"eq.{application_id}",
            "select": "id,application_id,uploaded_document_id,check_code,check_name,status,message,fix_suggestion,details,created_at",
            "order": "created_at.asc",
        },
    )
    public = [_public_result(row) for row in rows]
    return {"application_id": application_id, "results": public, "summary": _summary(public)}
