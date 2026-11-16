"""A small route used to prove that the admin check works."""

from fastapi import APIRouter, Depends

from app.auth import CurrentUser, require_admin

router = APIRouter()


@router.get("/admin/ping")
def admin_ping(_: CurrentUser = Depends(require_admin)) -> dict[str, str | bool]:
    return {"ok": True, "message": "admin access granted"}
