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
    # Largest upload this API will accept, in megabytes. A checklist item can be smaller.
    MAX_UPLOAD_MB: int = 5

    # Optional full path to tesseract.exe. Empty means "use the system PATH".
    TESSERACT_CMD: str = ""
    # Optional folder that contains pdftoppm.exe. Empty means "use the system PATH".
    POPPLER_PATH: str = ""
    # Tesseract language codes. eng+tam reads English and Tamil in one pass.
    OCR_LANGS: str = "eng+tam"
    # Stop one OCR call if it runs longer than this many seconds.
    OCR_TIMEOUT_SECONDS: int = 40
    # Dots per inch used when a PDF page is turned into an image.
    OCR_PDF_DPI: int = 200
    # Only the first this-many PDF pages are read. The real page count is still recorded.
    OCR_MAX_PDF_PAGES: int = 2
    # Refuse an image with more pixels than this. Also sets Pillow's bomb limit.
    OCR_MAX_PIXELS: int = 25000000

    # Gemini reads masked text and writes simple explanations. The key stays on the server.
    GEMINI_API_KEY: str = ""
    # The only model name the app may use. Change it here, not in the code.
    GEMINI_MODEL: str = "gemini-3.8-flash"
    # Seconds to wait for one Gemini call.
    AI_TIMEOUT_SECONDS: int = 30
    # Largest reply we ask Gemini to write.
    AI_MAX_OUTPUT_TOKENS: int = 800
    # Longest masked OCR text we send for one document.
    AI_MAX_INPUT_CHARS: int = 6000
    # How many AI calls one signed-in person may make per UTC day. The count resets on restart.
    AI_MAX_CALLS_PER_USER_PER_DAY: int = 80
    # When false, AI routes say assistance is turned off and the rest of the app still works.
    AI_ENABLED: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
