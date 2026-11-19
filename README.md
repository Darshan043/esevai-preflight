# e-Sevai Pre-Flight – AI-Powered Government Document Readiness Assistant

Checks whether a citizen's documents are complete and readable before they are submitted through Tamil Nadu e-Sevai.

## Planned tech stack

- Frontend: Next.js, TypeScript, Tailwind CSS (deployed on Vercel)
- Backend: Python FastAPI (deployed on Render with Docker)
- Data: Supabase (Postgres, Auth, Storage)
- AI: Google Gemini API
- Document processing: Tesseract OCR (English and Tamil), OpenCV, pdf2image (Poppler)

## Planned folder structure

```
/frontend     Next.js application
/backend      FastAPI application
/docs         Setup notes, service templates, step reports
/supabase     Database and storage configuration
```

## Status

Step 13 complete – Docker images for the frontend and backend. Supabase and Gemini stay outside the containers. The backend image includes Tesseract (`eng` and `tam`) and Poppler. Secrets are injected at run time and are never copied into image layers.

## Authentication

A citizen signs up or logs in through Supabase Auth in the browser. The anon key stays in the frontend. The service-role key stays in `backend/.env` and is never sent to the browser.

Next.js `src/proxy.ts` refreshes the session and sends visitors who are not signed in from `/dashboard`, `/admin`, and `/applications` to `/login`. Signed-in visitors are sent from `/login` and `/signup` to `/dashboard`. The server checks the user with `getUser()`. The login `next` path must start with a single `/`.

## Pages

| Route | Access |
| --- | --- |
| `/` | Public |
| `/services` | Public |
| `/services/[slug]` | Public |
| `/login` | Public |
| `/signup` | Public |
| `/dashboard` | Protected |
| `/applications` | Protected |
| `/applications/[id]` | Protected, owner only |
| `/applications/[id]/report` | Protected, owner only |
| `/admin` | Protected, admin only (overview) |
| `/admin/services` | Protected, admin only |
| `/admin/services/new` | Protected, admin only |
| `/admin/services/[id]` | Protected, admin only |
| `/admin/checks` | Protected, admin only |

The FastAPI backend checks the access token on `GET /me` and every `/admin/*` route. It accepts HS256 tokens signed with `SUPABASE_JWT_SECRET` and ES256/RS256 tokens checked against the project JWKS. If those checks cannot be completed, it asks Supabase Auth to accept or reject the token. The role comes from the `profiles` table, not from the browser. New accounts are `citizen`. An admin is created only by `supabase/scripts/promote_admin.sql`. Admins can open `/admin`. Citizens see an access-denied page. Hiding a link is not security: every admin API uses `require_admin`.

Frontend env names: `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`.
Backend env names: `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWT_SECRET`, `MAX_UPLOAD_MB`, `GEMINI_API_KEY`, `GEMINI_MODEL`. The Gemini key stays in `backend/.env` and is never sent to the browser. At deployment, set `GEMINI_API_KEY` and `GEMINI_MODEL` in Render as well.

## Uploads

A citizen uploads one file per checklist slot. The backend accepts JPG, JPEG, PNG, and PDF only. The size limit is the smaller of that slot's `max_size_mb` and `MAX_UPLOAD_MB` (default 5 MB). The private Storage path is `{user_id}/{application_id}/{required_document_code}-{8-char-random}-{sanitized_filename}`.

Only the owner can upload, preview, replace, or delete a file. An admin cannot open another person's files. Preview uses a new signed URL that lasts 300 seconds. The browser asks for a fresh link on every Preview click and does not save it.

## OCR

After a file is stored, the backend reads it on the server. It records sharpness (Laplacian variance), brightness, contrast, tilt, page count, and OCR confidence. Tesseract reads English and Tamil (`eng+tam`). Poppler turns the first PDF pages into images.

Optional environment variables: `TESSERACT_CMD`, `POPPLER_PATH`, `OCR_LANGS` (default `eng+tam`), and `OCR_TIMEOUT_SECONDS` (default 40). `OCR_PDF_DPI`, `OCR_MAX_PDF_PAGES`, and `OCR_MAX_PIXELS` are in `backend/.env.example`.

Only masked text is stored. A 12-digit or 16-digit ID number is saved as `XXXX XXXX 1234` or `XXXX XXXX XXXX 1234`. The raw OCR text is not written to the database, logs, or API responses.

Step 14 must include Tesseract with `eng` and `tam` trained data, and Poppler, in the Docker image.

Try one local file without the database:

```powershell
cd backend
.\.venv\Scripts\python.exe scripts\ocr_demo.py C:\path\to\document.jpg
```

## Validation

After a document is read, the checklist can run config-driven checks. The rules live on each `required_documents` row (`keywords`, `required_fields`, `rules`, `validity_days`). The engine does not hard-code one service.

Checks:

- Photo quality: sharpness, blank page, size, brightness, tilt, and OCR confidence
- Document type: English or Tamil keywords, with a close spelling accepted
- Required details: name, date, and number when the row asks for them
- ID number: Verhoeff checksum when `rules.id_number_pattern` is set. Only the last 4 digits are kept
- Document date: too old, missing, or in the future when an age limit is set
- Name match across documents when `rules.check_name_match` is true
- Missing mandatory slots

If a rule key is missing, the defaults are: blur below 100 fails, a blank page fails, a small photo warns, brightness outside 40–220 warns, OCR confidence below 40 warns, and tilt above 15 degrees warns.

Name and date reading uses a trusted Gemini extraction when one is saved. Otherwise it stays a best guess from labels and simple patterns. Gemini never changes a pass or fail result. The readiness score is a separate calculation over those results (see [Report](#report)).

`POST /applications/{id}/validate` replaces saved results. `GET /applications/{id}/validation` reads them. Both require the owner.

## AI assistance

Gemini does two jobs. It reads one document's already-masked OCR text into a small set of fields, and it rewrites warning and fail messages into short English or Tamil sentences. The rule engine remains the authority for every check.

What is sent:

- Masked OCR for one document, cut off at 6,000 characters, inside a data tag the model is told not to obey
- Check code, status, short message, fix suggestion, and the document's display name

What is not sent: storage paths, user ids, email addresses, file bytes, images, or unmasked ID numbers.

Limits: one call waits `AI_TIMEOUT_SECONDS` (default 30). A reply is capped by `AI_MAX_OUTPUT_TOKENS` (default 800). The smoke test uses its own 1,024-token cap. Each person may make `AI_MAX_CALLS_PER_USER_PER_DAY` calls (default 80). The count is kept in memory and resets when the server restarts. Set `AI_ENABLED=false` to turn the AI routes off without stopping uploads or checks.

The model name comes only from `GEMINI_MODEL`. The code default is `gemini-3.8-flash`. After repeated Gemini 3.8 Flash HTTP 503/504 and 429 errors, the configured model is `gemini-3.5-flash-lite`. See [docs/ai-design.md](docs/ai-design.md) and [docs/step-reports/step-09-report.md](docs/step-reports/step-09-report.md).

Unknown extra keys on an extraction JSON object are ignored. Known fields stay strict. Gemini never changes a pass or fail result.

## Application workspace

On `/applications/[id]`, from the `lg` breakpoint:

- Left: the five document cards (upload, replace, delete, re-read, quality, OCR text, AI-extracted details).
- Right: a sticky readiness panel with the full checklist, passed and failed checks, Re-run checks, Explain issues in simple words, and Generate readiness report.

Below that breakpoint the page is a single column, with the results panel first. The same validation state and API calls are reused. Browser verification of this layout is still pending.

## Report

`POST /applications/{id}/report` re-runs the checklist checks, scores them with a fixed formula, and saves `readiness_score`, `status = checked`, and `summary.report`. `GET /applications/{id}/report` returns that object plus `is_current` (false when a file changed after the report time).

The report holds service and document display names, check messages, fix suggestions, counts, the score, the label, next steps, and the carry list. It does not hold OCR text, holder names, ID numbers, storage paths, or emails. The formula and two worked examples are in [docs/readiness-scoring.md](docs/readiness-scoring.md).

Open `/applications/[id]/report` to see the score, what to do next, each document, and the carry list. **Print / Save as PDF** uses the browser print dialog (`window.print()`). There is no server-side PDF export in this step. Replacing or deleting a file returns the application to draft and clears the saved report.

## Admin

Signed-in admins open `/admin` for usage totals (users, applications, reports, average score), a label breakdown, top failure reasons, per-service numbers, and recent checks. Users in those tables are shown as `User #` plus six hash characters. Files, OCR text, storage paths, emails, and full user ids are never returned.

`/admin/services` lists every service, including drafts. New services start inactive and unverified. Duplicate always creates a draft copy. A slug cannot change after the first application. Delete is allowed only when the service has never been used; otherwise deactivate it. The same lock applies to a required-document code after a file has been uploaded.

Invalid rules cannot be saved. The Step 8 engine reads this configuration at runtime. See [docs/admin-guide.md](docs/admin-guide.md).

The overview page can preview data retention. `POST /admin/cleanup` defaults to a dry run and returns counts only.

Offline demo (no database):

```powershell
cd backend
.\.venv\Scripts\python.exe scripts\admin_demo.py
```

## Database

The schema, security rules, storage bucket, and Community Certificate seed are SQL files. Run them yourself in the Supabase SQL Editor. The order and expected result of each script are in [docs/step-03-run-order.md](docs/step-03-run-order.md). The table layout is explained in [docs/database-design.md](docs/database-design.md).

## How to run

The sample documents from Step 1 stay in `sample-docs/` and are Git-ignored.

### Backend (Windows PowerShell)

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Run the tests from `backend` with the virtual environment activated:

```powershell
pytest
```

### Backend (macOS / Linux)

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
pytest
```

### Frontend (Windows, macOS, and Linux)

```powershell
cd frontend
npm install
npm run dev
```

Open http://localhost:3000 while the backend is running on port 8000.

## Docker

Requires Docker Desktop with Linux containers (Engine 29+ and Compose v2). Do not copy `.env` files into an image.

### Environment

- Backend secrets stay in `backend/.env` (gitignored). Compose loads that file at **run** time.
- Frontend public names stay in `frontend/.env.local`. Pass them at **build** time with `--env-file frontend/.env.local`.
- For local Compose, keep `ENVIRONMENT=development` so localhost origins are allowed.
- `NEXT_PUBLIC_API_URL` must be the URL the **browser** uses (`http://localhost:8000` locally), not `http://backend:8000`.
- The service-role key must never be a frontend build-arg.

### Build and start

From the repository root:

```powershell
docker compose --env-file frontend/.env.local up --build
```

Detached:

```powershell
docker compose --env-file frontend/.env.local up --build -d
```

### URLs

- Frontend: http://localhost:3000
- Backend health: http://localhost:8000/health
- Backend ready: http://localhost:8000/health/ready

### Logs and stop

```powershell
docker compose logs -f
docker compose logs -f backend
docker compose logs -f frontend
docker compose stop
docker compose down
```

`down` stops and removes the containers. Images stay until you run `docker compose down --rmi local`.

### Render

Build the backend image from `backend/Dockerfile`. Set the production variable names in the Render dashboard (see [docs/deployment-env-checklist.md](docs/deployment-env-checklist.md)). Do not bake `backend/.env` into the image. Use `ENVIRONMENT=production` and an `https` `ALLOWED_ORIGINS` list. One uvicorn worker is required because rate limits and the daily AI cap live in process memory. The frontend may stay on Vercel; if you also run the frontend image, rebuild it whenever `NEXT_PUBLIC_API_URL` changes.

## Errors, limits, and retention

Every API error is `{"error":{"code","message","request_id"}}`. Validation errors may also include `fields`. The browser still understands the older `{"detail": "..."}` shape.

`GET /health` is a liveness check. `GET /health/ready` checks the database, storage, and OCR. Tamil OCR is optional. In production, `/docs` is off unless `ENABLE_DOCS=true`.

Rate limits live in this process and reset on restart. Defaults: 30 uploads/hour, 60 process/hour, 60 validate-or-report/hour, 120 admin writes/hour, 30 `/health/ready` calls/minute per IP.

Count unused applications (dry run):

```powershell
cd backend
.\.venv\Scripts\python.exe scripts\cleanup_old_data.py
```

Owner-run smoke test (does not create rows):

```powershell
cd backend
.\.venv\Scripts\python.exe scripts\e2e_smoke.py --selftest
.\.venv\Scripts\python.exe scripts\e2e_smoke.py
```

Production variable names are listed in [docs/deployment-env-checklist.md](docs/deployment-env-checklist.md). Do not put secret values in that file.
