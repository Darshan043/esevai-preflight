"""A simple health check so the frontend can see that the API is running."""

from datetime import datetime, timezone

from fastapi import APIRouter

from app.config import settings

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    # UTC timestamp so the frontend can show when this answer was made.
    current_time = datetime.now(timezone.utc).isoformat()
    return {
        "status": "ok",
        "service": "esevai-preflight-backend",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "time": current_time,
    }
