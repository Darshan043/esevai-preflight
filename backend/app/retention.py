"""Find and optionally delete applications older than DATA_RETENTION_DAYS.

Storage objects are removed first. If a file delete fails, the application row
is left in place. Logs and responses are counts only.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from app.config import settings
from app.supabase_client import SupabaseRequestError, delete_objects, delete_rows, get_rows

logger = logging.getLogger(__name__)

DeleteObjects = Callable[[list[str]], None]
DeleteRows = Callable[[str, dict[str, str]], None]
GetRows = Callable[[str, dict[str, str]], list[dict[str, Any]]]


def cutoff_stamp(days: int, now: datetime | None = None) -> str:
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    return (current - timedelta(days=max(1, days))).isoformat()


def find_expired(
    days: int,
    *,
    reader: GetRows = get_rows,
    now: datetime | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    cutoff = cutoff_stamp(days, now)
    applications = reader(
        "applications",
        {
            "updated_at": f"lt.{cutoff}",
            "select": "id,updated_at",
            "limit": "5000",
        },
    )
    ids = [str(row.get("id") or "") for row in applications if row.get("id")]
    files: list[dict[str, Any]] = []
    for application_id in ids:
        files.extend(
            reader(
                "uploaded_documents",
                {
                    "application_id": f"eq.{application_id}",
                    "select": "id,application_id,storage_path",
                    "limit": "500",
                },
            )
        )
    return applications, files


def cleanup_expired(
    *,
    dry_run: bool = True,
    days: int | None = None,
    reader: GetRows = get_rows,
    remove_objects: DeleteObjects = delete_objects,
    remove_rows: DeleteRows = delete_rows,
    now: datetime | None = None,
) -> dict[str, Any]:
    window = int(days if days is not None else settings.DATA_RETENTION_DAYS)
    applications, files = find_expired(window, reader=reader, now=now)
    summary = {
        "dry_run": dry_run,
        "days": window,
        "applications": len(applications),
        "files": len(files),
        "deleted_applications": 0,
        "deleted_files": 0,
        "skipped_applications": 0,
    }
    logger.info(
        "cleanup scan dry_run=%s days=%s applications=%s files=%s",
        dry_run,
        window,
        summary["applications"],
        summary["files"],
    )
    if dry_run:
        return summary

    files_by_app: dict[str, list[str]] = {}
    for row in files:
        app_id = str(row.get("application_id") or "")
        path = str(row.get("storage_path") or "")
        if app_id and path:
            files_by_app.setdefault(app_id, []).append(path)

    deleted_apps = 0
    deleted_files = 0
    skipped = 0
    for application in applications:
        app_id = str(application.get("id") or "")
        if not app_id:
            continue
        paths = files_by_app.get(app_id, [])
        try:
            if paths:
                remove_objects(paths)
                deleted_files += len(paths)
        except SupabaseRequestError:
            skipped += 1
            logger.info("cleanup skipped application because storage delete failed")
            continue
        try:
            remove_rows("applications", {"id": f"eq.{app_id}"})
        except SupabaseRequestError:
            skipped += 1
            logger.info("cleanup skipped application because row delete failed")
            continue
        deleted_apps += 1

    summary["deleted_applications"] = deleted_apps
    summary["deleted_files"] = deleted_files
    summary["skipped_applications"] = skipped
    logger.info(
        "cleanup apply days=%s deleted_applications=%s deleted_files=%s skipped=%s",
        window,
        deleted_apps,
        deleted_files,
        skipped,
    )
    return summary
