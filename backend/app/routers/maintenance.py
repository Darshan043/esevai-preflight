"""Admin-only data retention. Dry-run is the default."""

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field

from app.auth import CurrentUser
from app.limits.ratelimit import require_admin_write
from app.retention import cleanup_expired

router = APIRouter()


class CleanupBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dry_run: bool = Field(default=True)


@router.post("/admin/cleanup")
def run_cleanup(
    body: CleanupBody | None = None,
    _: CurrentUser = Depends(require_admin_write),
) -> dict[str, Any]:
    """Count or delete applications older than DATA_RETENTION_DAYS. Counts only."""
    dry_run = True if body is None else body.dry_run
    return cleanup_expired(dry_run=dry_run)
