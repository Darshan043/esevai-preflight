# Deployment environment checklist

Names only. Do not paste secret values into this file, Git, or chat.

`NEXT_PUBLIC_*` values are inlined at Next.js **build** time. A redeploy is required after changing them.

## Backend (Render)

Required in production (`ENVIRONMENT=production`):

- `ENVIRONMENT` — must be `production`
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `ALLOWED_ORIGINS` — a single `https://` origin (`<APP_URL>`). No `*`, no localhost, no trailing slash
- `GEMINI_API_KEY` — required when `AI_ENABLED=true`
- `GEMINI_MODEL` — required when `AI_ENABLED=true`

Set these as well for the demo:

- `SUPABASE_JWT_SECRET` — required if the project uses HS256
- `AI_ENABLED`
- `AI_MAX_CALLS_PER_USER_PER_DAY`
- `MAX_UPLOAD_MB` (default `5`)
- `OCR_LANGS` (default `eng+tam`)
- `OCR_PDF_DPI` — use `150` on the 512 MB free instance
- `OCR_MAX_PDF_PAGES` — use `2` on the free instance (`1` if OCR runs out of memory)
- `DATA_RETENTION_DAYS` (default `30`)
- `ENABLE_DOCS` — `false` in production

Usually leave unset on Render (the image / defaults already handle them):

- `APP_VERSION`
- `TESSERACT_CMD` / `POPPLER_PATH`
- `OCR_TIMEOUT_SECONDS`
- `OCR_MAX_PIXELS`
- `AI_TIMEOUT_SECONDS`
- `AI_MAX_OUTPUT_TOKENS`
- `AI_MAX_INPUT_CHARS`
- `RATE_LIMIT_UPLOADS_PER_HOUR`
- `RATE_LIMIT_PROCESS_PER_HOUR`
- `RATE_LIMIT_VALIDATE_REPORT_PER_HOUR`
- `RATE_LIMIT_ADMIN_WRITES_PER_HOUR`
- `RATE_LIMIT_READY_PER_MINUTE`

Do **not** set `PORT`. Render provides it.

Legacy names that this app does not require for production AI:

- `ANTHROPIC_API_KEY`
- `CLAUDE_MODEL`

## Frontend (Vercel)

Exactly these three names:

- `NEXT_PUBLIC_API_URL` — `https` API origin (`<API_URL>`), no trailing slash
- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`

The service-role key must never be set in the frontend.
