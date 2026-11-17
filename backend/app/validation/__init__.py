"""Config-driven document checks. The functions do not call Supabase."""

from app.validation.engine import validate_application

__all__ = ["validate_application"]
