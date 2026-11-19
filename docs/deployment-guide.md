# Live deployment guide (Render + Vercel)

Do not paste keys, passwords, or tokens into this file, Git, or chat. This guide lists **names** and placeholders only.

Placeholders:

- `<RENDER_NAME>` — Render web service name
- `<VERCEL_NAME>` — Vercel project name
- `<API_URL>` — `https://<RENDER_NAME>.onrender.com` (no trailing slash)
- `<APP_URL>` — `https://<VERCEL_NAME>.vercel.app` (no trailing slash)

This app’s live AI provider is **Google Gemini**. Production needs `GEMINI_API_KEY` and `GEMINI_MODEL`. `ANTHROPIC_API_KEY` and `CLAUDE_MODEL` are unused legacy names.

`NEXT_PUBLIC_*` values are inlined when Vercel **builds** the frontend. After you change one, you must redeploy.

## 1. Pre-flight

1. Supabase project is ready: schema/RLS/storage/seed SQL have been run, bucket `documents` is **private**, and at least one profile is `admin` (`supabase/scripts/promote_admin.sql`).
2. Choose `<RENDER_NAME>` and `<VERCEL_NAME>` (letters, numbers, hyphens).
3. Push `main` to GitHub (`https://github.com/Darshan043/esevai-preflight.git`).
4. Keep `backend/.env` and `frontend/.env.local` on your PC only. Never upload them to Render/Vercel as files.

## 2. Render (backend)

Dashboard: **New +** → **Web Service** → connect the **private** GitHub repo.

| Field | Value |
| --- | --- |
| Language / Runtime | Docker |
| Root Directory | `backend` |
| Dockerfile path | `./Dockerfile` |
| Region | Singapore (closest to India) |
| Instance type | Free |
| Health Check Path | `/health` |
| Auto-Deploy | On |

Do **not** set `PORT`. Render provides it (often `10000`). The image listens on `0.0.0.0` and `${PORT:-8000}`, with `--proxy-headers` and `--forwarded-allow-ips=*`.

### Environment variables

Set these in Render → Environment. Values come from the Supabase and Gemini dashboards, or from this table. Never paste the values into Git.

| Name | Where the value comes from | Required |
| --- | --- | --- |
| `ENVIRONMENT` | Type `production` | Required |
| `ALLOWED_ORIGINS` | `<APP_URL>` — `https`, no trailing slash, no `*`, no localhost | Required |
| `SUPABASE_URL` | Supabase → Project Settings → API → Project URL | Required |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase → Project Settings → API → `service_role` (secret) | Required |
| `SUPABASE_JWT_SECRET` | Supabase → Project Settings → API → JWT secret | Required if the project uses HS256 |
| `GEMINI_API_KEY` | Google AI Studio / Gemini key | Required when `AI_ENABLED=true` |
| `GEMINI_MODEL` | Model name you already tested locally (for example the value in `backend/.env`) | Required when `AI_ENABLED=true` |
| `AI_ENABLED` | `true` | Required |
| `AI_MAX_CALLS_PER_USER_PER_DAY` | Same as local, or `80` | Optional (default 80) |
| `MAX_UPLOAD_MB` | `5` | Optional (default 5) |
| `OCR_LANGS` | `eng+tam` | Optional (default `eng+tam`) |
| `OCR_PDF_DPI` | `150` (keeps memory down on the 512 MB free instance) | Recommended |
| `OCR_MAX_PDF_PAGES` | `2` | Recommended |
| `DATA_RETENTION_DAYS` | `30` | Optional (default 30) |
| `ENABLE_DOCS` | `false` | Recommended in production |

Optional names the image already understands, usually leave unset on Render: `APP_VERSION`, `TESSERACT_CMD`, `POPPLER_PATH`, `OCR_TIMEOUT_SECONDS`, `OCR_MAX_PIXELS`, `AI_TIMEOUT_SECONDS`, `AI_MAX_OUTPUT_TOKENS`, `AI_MAX_INPUT_CHARS`, `RATE_LIMIT_UPLOADS_PER_HOUR`, `RATE_LIMIT_PROCESS_PER_HOUR`, `RATE_LIMIT_VALIDATE_REPORT_PER_HOUR`, `RATE_LIMIT_ADMIN_WRITES_PER_HOUR`, `RATE_LIMIT_READY_PER_MINUTE`.

Do not set `ANTHROPIC_API_KEY` or `CLAUDE_MODEL` unless you are only preserving empty legacy names. Live AI does not read them.

### Expected result

The first Docker build takes several minutes (Tesseract `eng`+`tam` and Poppler). Then:

- `<API_URL>/health` returns `ok`
- `<API_URL>/health/ready` shows `ocr=ok` and `tamil_ocr=yes`

If the instance is waking up, wait 30–60 seconds and try `/health` again.

## 3. Vercel (frontend)

Vercel builds Next.js **natively**. It does **not** use `frontend/Dockerfile`.

1. **Add New Project** → import the same GitHub repo.
2. Framework Preset = **Next.js**.
3. Root Directory = `frontend`.
4. Set these three names **before** the first deploy:

| Name | Value |
| --- | --- |
| `NEXT_PUBLIC_API_URL` | `<API_URL>` |
| `NEXT_PUBLIC_SUPABASE_URL` | Same Supabase Project URL as the backend |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase anon (publishable) key. Never the service-role key |

5. Deploy.

Changing any `NEXT_PUBLIC_*` name later requires a **redeploy**. Saving the variable is not enough.

## 4. Supabase URL configuration

Supabase → **Authentication** → **URL Configuration**:

- Site URL = `<APP_URL>`
- Redirect URLs: add `<APP_URL>/**`
- Keep `http://localhost:3000/**` for local development

Confirm the email-confirmation setting matches what you already tested locally (confirmation on or off).

## 5. If the Vercel URL is not what you predicted

1. Copy the real frontend origin (https, no trailing slash).
2. Update `ALLOWED_ORIGINS` on Render to that origin. Render will redeploy.
3. Update Supabase Site URL and Redirect URLs to match.
4. If `NEXT_PUBLIC_API_URL` was wrong, fix it on Vercel and **redeploy**.

## 6. Live smoke test (PowerShell)

The script is read-only. It does not create database or storage rows and it does not need a password. Run it from a terminal; do not put these values in files.

```powershell
cd D:\esevai-preflight\backend
$env:E2E_BACKEND_URL="<API_URL>"
$env:E2E_FRONTEND_URL="<APP_URL>"
.\.venv\Scripts\python.exe scripts\e2e_smoke.py
```

Expected: `e2e smoke: all checks passed`.

The first request may take 30–60 seconds because the free Render instance is waking up. Use the dedicated test account only for the **manual** live rows in `docs/test-log.md`, not for this script.

## 7. Manual live test checklist

Fill the **Live deployment** rows (L1–L5) in [test-log.md](test-log.md). Also run the citizen, admin, privacy, and phone tests against the live URLs when you can.

## 8. Keeping the demo reliable

- Render **free** instances sleep after about **15 minutes** idle. Open `<API_URL>/health` about **5 minutes** before any demo.
- Optionally set a free uptime monitor to GET `/health` every 5 minutes. Do not poll `/health/ready` that often (it is rate-limited).
- Render free has **512 MB RAM**. If uploads crash with out-of-memory, set `OCR_PDF_DPI=120` and `OCR_MAX_PDF_PAGES=1`, then redeploy.

## 9. Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| Browser CORS error | `ALLOWED_ORIGINS` is not exactly `<APP_URL>` | Set the https origin with no slash, no `*`, no localhost; wait for Render to redeploy |
| 502 / 503 right after deploy | Container still starting, or free instance waking | Wait 30–60 s; hit `/health`; check Render logs |
| `/health/ready` degraded | One of `database`, `storage`, `ocr` failed, or `tamil_ocr=no` | Read `checks` in the JSON. Tamil missing means `tesseract-ocr-tam` did not install; others mean Supabase URL/key or the `documents` bucket |
| Backend refuses to start | Production startup missing required names | Render logs name the missing variables (`SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `ALLOWED_ORIGINS`, and Gemini names when `AI_ENABLED=true`) |
| Login redirects to the wrong site | Supabase Site URL / Redirect URLs | Set Site URL to `<APP_URL>` and add `<APP_URL>/**` |
| Frontend still calls localhost or an old API | `NEXT_PUBLIC_*` inlined at build time | Change the Vercel env name and **redeploy** |
| Tamil OCR missing | Image built without `tesseract-ocr-tam` | Confirm Root Directory is `backend` and the Dockerfile still installs `tesseract-ocr-tam`; rebuild |
| Out-of-memory during OCR | 512 MB free instance, large PDF | `OCR_PDF_DPI=120` and `OCR_MAX_PDF_PAGES=1` |
| 429 too many requests | In-memory rate limiter | Wait; do not hammer `/health/ready`; limits reset on restart |
| Images / preview blocked | CSP `connect-src` / `img-src` | Confirm `NEXT_PUBLIC_SUPABASE_URL` was set **before** the Vercel build; redeploy |
| Gemini errors | Key, credit, or model name | Check `GEMINI_API_KEY` and `GEMINI_MODEL` on Render (not the frontend) |

## 10. Rollback

- Render: Dashboard → the web service → **Releases** (or Events) → deploy a previous successful image.
- Vercel: Project → **Deployments** → promote / redeploy a previous production deployment.
- If a key was ever shown in logs, a screenshot, or Git: rotate it in Supabase / Google AI Studio, update Render (and Vercel only for the anon key), and redeploy.
