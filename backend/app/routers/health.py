"""A simple health check so the frontend can see that the API is running."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.config import settings
from app.limits.ratelimit import limit_ready_ip
from app.ready import ready_body

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


@router.get("/health/ready")
def ready(_: None = Depends(limit_ready_ip)) -> JSONResponse:
    """Database, storage, and OCR. Tamil OCR is optional."""
    status, body = ready_body()
    return JSONResponse(status_code=status, content=body)
