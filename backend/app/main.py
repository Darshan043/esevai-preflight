"""FastAPI application entry point.

Run from the backend folder:
    uvicorn app.main:app --reload --port 8000
"""

import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.routers import admin, ai, documents, health, me, validation

logger = logging.getLogger(__name__)


def allowed_origins() -> list[str]:
    # "http://localhost:3000,http://127.0.0.1:3000" becomes a list of origins.
    return [origin.strip() for origin in settings.ALLOWED_ORIGINS.split(",") if origin.strip()]


app = FastAPI(title="e-Sevai Pre-Flight API", version=settings.APP_VERSION)

# Browsers block calls from another origin unless we explicitly allow it.
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(me.router)
app.include_router(admin.router)
app.include_router(documents.router)
app.include_router(validation.router)
app.include_router(ai.router)


@app.exception_handler(Exception)
async def unexpected_error(_request: object, exc: Exception) -> JSONResponse:
    """A generic message. The log records the exception type and nothing else."""
    if isinstance(exc, HTTPException):
        raise exc
    logger.info("unhandled error_type=%s", type(exc).__name__)
    return JSONResponse(status_code=500, content={"detail": "Something went wrong. Please try again."})
