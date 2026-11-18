"""Build, save, and read the readiness report.

The service-role key bypasses row-level security, so every route checks that
the application's user_id is the caller. Someone else's row answers 404.
The report never includes OCR text, names, ID numbers, or storage paths.
The score is computed from saved checks only. AI advice never changes it.
"""

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app.auth import CurrentUser, get_current_user
from app.report.builder import build_report, is_report_current
from app.report.hygiene import with_report
from app.routers.validation import run_and_store_validation
from app.supabase_client import SupabaseRequestError, get_rows, update_rows

router = APIRouter()

# Keys the browser may see. Extra keys from a bad saved row are dropped.
_REPORT_KEYS = (
    "generated_at",
    "score",
    "label",
    "counts",
    "documents",
    "application_issues",
    "next_steps",
    "carry_list",
)


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


def _public_report(value: object) -> dict[str, Any] | None:
    """Keep only the fields a citizen may see."""
    if not isinstance(value, dict):
        return None
    return {key: value.get(key) for key in _REPORT_KEYS if key in value}


@router.post("/applications/{application_id}/report")
def create_report(application_id: str, user: CurrentUser = Depends(get_current_user)) -> dict[str, Any]:
    """Refresh checks, score them, save the report, and return it."""
    application = _owned_application(application_id, user.user_id)
    uploads = get_rows(
        "uploaded_documents",
        {
            "application_id": f"eq.{application_id}",
            "user_id": f"eq.{user.user_id}",
            "select": "id,required_document_id,status,updated_at,created_at",
        },
    )
    if not uploads:
        raise HTTPException(status_code=400, detail="Upload at least one document first")
    if any(row.get("status") in {"uploaded", "processing"} for row in uploads):
        raise HTTPException(
            status_code=409,
            detail="Some documents are still being read – wait a moment and try again",
        )

    payload = run_and_store_validation(application_id, user.user_id)
    services = get_rows(
        "services",
        {
            "id": f"eq.{application['service_id']}",
            "select": "id,name_en,name_ta,slug",
            "limit": "1",
        },
    )
    service = services[0] if services else {"id": application.get("service_id")}
    required = payload["required"]
    saved = payload["results"]
    report = build_report(
        application,
        service,
        required,
        uploads,
        saved,
        datetime.now(timezone.utc),
    )

    # Read the latest summary so we keep keys that were not cleared by validate.
    fresh_rows = get_rows(
        "applications",
        {"id": f"eq.{application_id}", "select": "id,summary", "limit": "1"},
    )
    summary = fresh_rows[0].get("summary") if fresh_rows else application.get("summary")
    try:
        updated = update_rows(
            "applications",
            {"id": f"eq.{application_id}", "user_id": f"eq.{user.user_id}"},
            {
                "readiness_score": report["score"],
                "status": "checked",
                "summary": with_report(summary, report),
            },
        )
    except SupabaseRequestError as exc:
        raise HTTPException(
            status_code=502,
            detail="The report could not be saved. Please try again.",
        ) from exc
    if not updated:
        raise HTTPException(status_code=502, detail="The report could not be saved. Please try again.")
    public = _public_report(report)
    if public is None:
        raise HTTPException(status_code=502, detail="The report could not be saved. Please try again.")
    return public


@router.get("/applications/{application_id}/report")
def read_report(application_id: str, user: CurrentUser = Depends(get_current_user)) -> dict[str, Any]:
    """Return the saved report, or null when there is none."""
    application = _owned_application(application_id, user.user_id)
    summary = application.get("summary") if isinstance(application.get("summary"), dict) else {}
    report = _public_report(summary.get("report") if isinstance(summary, dict) else None)
    if report is None:
        return {"report": None, "is_current": False}
    uploads = get_rows(
        "uploaded_documents",
        {
            "application_id": f"eq.{application_id}",
            "user_id": f"eq.{user.user_id}",
            "select": "id,updated_at,created_at",
        },
    )
    return {"report": report, "is_current": is_report_current(report.get("generated_at"), uploads)}
