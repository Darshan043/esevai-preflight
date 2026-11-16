"""Load settings from environment variables.

The app starts even when the optional keys are empty. Later steps will fill them in.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Where this copy of the API is running: development, staging, or production.
    ENVIRONMENT: str = "development"
    # Comma-separated list of browser origins allowed to call the API.
    ALLOWED_ORIGINS: str = "http://localhost:3000"
    APP_VERSION: str = "0.1.0"

    # Optional until later steps. Empty strings let the server start without them.
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    SUPABASE_JWT_SECRET: str = ""
    ANTHROPIC_API_KEY: str = ""
    CLAUDE_MODEL: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
