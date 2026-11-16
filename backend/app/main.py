"""FastAPI application entry point.

Run from the backend folder:
    uvicorn app.main:app --reload --port 8000
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import health


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
