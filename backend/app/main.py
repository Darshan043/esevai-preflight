"""FastAPI application entry point.

Run from the backend folder:
    uvicorn app.main:app --reload --port 8000
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.errors import http_exception_handler, unhandled_exception_handler, validation_exception_handler
from app.limits.size import BodySizeMiddleware
from app.logging_safe import RequestContextMiddleware, install_logging
from app.routers import admin, admin_config, admin_stats, ai, documents, health, maintenance, me, report, validation
from app.security_headers import SecurityHeadersMiddleware
from app.startup import docs_enabled, parse_origins, validate_settings


@asynccontextmanager
async def lifespan(_app: FastAPI):
    install_logging()
    validate_settings(settings)
    yield


def create_app() -> FastAPI:
    show_docs = docs_enabled(settings)
    application = FastAPI(
        title="e-Sevai Pre-Flight API",
        version=settings.APP_VERSION,
        lifespan=lifespan,
        docs_url="/docs" if show_docs else None,
        redoc_url="/redoc" if show_docs else None,
        openapi_url="/openapi.json" if show_docs else None,
    )
    # Last add_middleware is the outermost wrapper. CORS must wrap every response.
    application.add_middleware(BodySizeMiddleware)
    application.add_middleware(SecurityHeadersMiddleware)
    application.add_middleware(RequestContextMiddleware)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=parse_origins(settings.ALLOWED_ORIGINS),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )
    application.add_exception_handler(HTTPException, http_exception_handler)
    application.add_exception_handler(StarletteHTTPException, http_exception_handler)
    application.add_exception_handler(RequestValidationError, validation_exception_handler)
    application.add_exception_handler(Exception, unhandled_exception_handler)
    application.include_router(health.router)
    application.include_router(me.router)
    application.include_router(admin.router)
    application.include_router(admin_config.router)
    application.include_router(admin_stats.router)
    application.include_router(maintenance.router)
    application.include_router(documents.router)
    application.include_router(validation.router)
    application.include_router(ai.router)
    application.include_router(report.router)
    return application


app = create_app()
