"""Aggregate usage numbers for admins.

Statistics reflect current data; validation results are replaced whenever a
check is re-run. This module never returns files, OCR text, emails, or full
user ids.
"""

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, Query

from app.admin.stats import (
    ROW_CAP,
    activity,
    per_service,
    recent_checks,
    score_summary,
    top_failure_reasons,
    totals,
)
from app.auth import CurrentUser, require_admin
from app.supabase_client import count_rows, get_rows

router = APIRouter()


def _capped(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    return rows[:ROW_CAP], len(rows) >= ROW_CAP


@router.get("/admin/stats")
def read_stats(
    days: int = Query(default=14, ge=1, le=90),
    _: CurrentUser = Depends(require_admin),
) -> dict[str, Any]:
    # Statistics reflect current data; validation results are replaced whenever a check is re-run.
    profiles = get_rows("profiles", {"select": "id,role", "limit": str(ROW_CAP)})
    applications = get_rows(
        "applications",
        {
            "select": "id,service_id,user_id,status,readiness_score,summary,created_at,updated_at",
            "limit": str(ROW_CAP),
            "order": "created_at.desc",
        },
    )
    uploads = get_rows(
        "uploaded_documents",
        {"select": "id,application_id,status", "limit": str(ROW_CAP)},
    )
    services = get_rows("services", {"select": "id,slug,name_en", "limit": str(ROW_CAP)})
    results = get_rows(
        "validation_results",
        {"select": "check_code,check_name,status", "limit": str(ROW_CAP)},
    )
    _, profiles_capped = _capped(profiles)
    applications, applications_capped = _capped(applications)
    uploads, uploads_capped = _capped(uploads)
    results, results_capped = _capped(results)
    today = datetime.now(timezone.utc).date()
    return {
        "days": days,
        "totals": totals(profiles, applications, uploads),
        "score": score_summary(applications),
        "top_failure_reasons": top_failure_reasons(results),
        "per_service": per_service(services, applications),
        "activity": activity(applications, days, today),
        "recent_checks": recent_checks(applications, services, uploads, limit=10),
        "capped": profiles_capped or applications_capped or uploads_capped or results_capped,
        "footnote": "Statistics reflect current data; validation results are replaced whenever a check is re-run.",
    }


@router.get("/admin/applications")
def list_admin_applications(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    _: CurrentUser = Depends(require_admin),
) -> dict[str, Any]:
    total = count_rows("applications")
    offset = (page - 1) * page_size
    applications = get_rows(
        "applications",
        {
            "select": "id,service_id,user_id,status,readiness_score,summary,created_at,updated_at",
            "order": "created_at.desc",
            "limit": str(page_size),
            "offset": str(offset),
        },
    )
    services = get_rows("services", {"select": "id,name_en", "limit": str(ROW_CAP)})
    uploads = get_rows(
        "uploaded_documents",
        {"select": "application_id", "limit": str(ROW_CAP)},
    )
    items = recent_checks(applications, services, uploads, limit=page_size)
    return {
        "items": items,
        "page": page,
        "page_size": page_size,
        "total": total,
        "footnote": "Statistics reflect current data; validation results are replaced whenever a check is re-run.",
    }
