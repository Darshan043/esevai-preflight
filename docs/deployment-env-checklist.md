# Deployment environment checklist

Names only. Do not paste secret values into this file, Git, or chat.

## Backend (Render)

Required in production (`ENVIRONMENT=production`):

- `ENVIRONMENT` — must be `production`
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `ALLOWED_ORIGINS` — comma-separated `https://` origins. No `*`, no localhost
- `GEMINI_API_KEY` — required when `AI_ENABLED=true`
- `GEMINI_MODEL` — required when `AI_ENABLED=true`

Usually also set:

- `SUPABASE_JWT_SECRET`
- `APP_VERSION`
- `MAX_UPLOAD_MB`
- `TESSERACT_CMD` / `POPPLER_PATH` if the binaries are not on `PATH`
- `OCR_LANGS` (default `eng+tam`)
- `AI_ENABLED`
- `AI_TIMEOUT_SECONDS`
- `ENABLE_DOCS` — leave empty or `false` in production
- `DATA_RETENTION_DAYS` (default 30)
- `RATE_LIMIT_UPLOADS_PER_HOUR`
- `RATE_LIMIT_PROCESS_PER_HOUR`
- `RATE_LIMIT_VALIDATE_REPORT_PER_HOUR`
- `RATE_LIMIT_ADMIN_WRITES_PER_HOUR`
- `RATE_LIMIT_READY_PER_MINUTE`

Legacy names that this app does not require for production AI:

- `ANTHROPIC_API_KEY`
- `CLAUDE_MODEL`

## Frontend (Vercel)

- `NEXT_PUBLIC_API_URL` — `https` API origin
- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`

The service-role key must never be set in the frontend.
