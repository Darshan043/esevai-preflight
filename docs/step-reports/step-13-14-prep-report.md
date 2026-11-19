# Steps 13–14 prep verification report

**Project:** e-Sevai Pre-Flight – AI-Powered Government Document Readiness Assistant

**Date:** 19 November 2026

**OS:** Windows 10 / PowerShell

**Scope:** Commit existing Docker work; automated Step 13 tests; Render/Vercel adjustments; owner test-log template; deployment guide. No live deploy.

## Gate

| Check | Result | Evidence |
| --- | --- | --- |
| B1 step reports 01–12 | PASS | `docs/step-reports/step-01-report.md` … `step-12-report.md` exist |
| B1 step commits | PASS | Step 1 `9f01613` `d19f803`; Step 2 `6cf6300` `92c0b76`; Step 3 `279cdbb` `dd2e2c8`; Step 4 `0f2aa25` `1cbef4b`; Step 5 `9d5cb3d` `7305173`; Step 6 `fed1070` `e1478b6`; Step 7 `dc09966` `22f8939`; Step 8 `9cbd4ef` `d1e2cd5`; Step 9 `70c4580` `37cf07d`; Step 10 `4586923` `2f473bd`; Step 11 `c45423b` `6e575c5`; Step 12 `8f5a421` `95d1ded` |
| B2 Docker files only | PASS | Uncommitted before commit 1: `backend/Dockerfile`, `frontend/Dockerfile`, both `.dockerignore`, `docker-compose.yml`, `frontend/next.config.ts`, `README.md`, `docs/SETUP_CHECKLIST.md` |
| B3 env names | PASS | Files exist and are gitignored. Backend: `SUPABASE_URL` set, `SUPABASE_SERVICE_ROLE_KEY` set, `SUPABASE_JWT_SECRET` set, `GEMINI_API_KEY` set, `GEMINI_MODEL` set, `AI_ENABLED` set, `ENVIRONMENT` not set (code default `development`), `ALLOWED_ORIGINS` not set (code default localhost). Frontend: `NEXT_PUBLIC_API_URL` set, `NEXT_PUBLIC_SUPABASE_URL` set, `NEXT_PUBLIC_SUPABASE_ANON_KEY` set. `git ls-files` has only `.env.example` files |
| B3 secret scan | PASS | No real secrets in tracked files or history. Pattern hits are redaction regexes, fake test tokens, report wording, and a `package-lock.json` integrity hash substring. Long JWT hits: 0. Long `sk-ant-` hits: 0. Commits mentioning `sk-ant-`: 2 (tests/docs). `.env` files were never committed |
| B4 database | PASS | `check_db.py` is not present. Read-only client check: `community-certificate` exists and is active; 5 active required documents; bucket `documents` exists and `public=false`; 1 admin profile. No rows created |
| B5 e2e smoke | PASS | Owner answered yes |

GATE PASSED.

## Checks

| Check | Result | Evidence | Reason if not PASS | Fix |
| --- | --- | --- | --- | --- |
| Automated tests before changes | PASS | pytest **143 passed**; frontend `node --experimental-strip-types --test` **35 passed**; `npm run lint` clean; `npm run build` succeeded | | |
| Automated tests after changes | PASS | pytest **143 passed**; frontend **35 passed**; lint clean; `npm run build` succeeded | | |
| Backend image PORT / proxy / OMP | PASS | `CMD` is `sh -c` with `--host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'`. `ENV OMP_THREAD_LIMIT=1`. One uvicorn worker. `HEALTHCHECK` uses `PORT` and `/health`. COPY stays inside `/backend`. User `appuser` (uid 10001). No `.env` in the image. Tesseract langs: `eng`, `osd`, `tam` | | |
| Docker run port 8000 | PASS | `docker run -p 8000:8000 -e PORT=8000 --env-file backend/.env` with `ENVIRONMENT=development`. Inside the container `/health` HTTP 200 and `/health/ready` `{"status":"ok","checks":{"database":"ok","storage":"ok","ocr":"ok","tamil_ocr":"yes"}}`. Uvicorn log: `http://0.0.0.0:8000` | | |
| Docker run port 10000 | PASS | `docker run -p 10000:10000 -e PORT=10000`. Uvicorn on `0.0.0.0:10000`. Host and in-container `/health` HTTP 200. Container stopped afterwards | | |
| Image size | PASS | `esevai-preflight-backend:latest` **819MB** | | |
| Compose build | PASS | `docker compose --env-file frontend/.env.local build` succeeded (did not publish port 3000). Compose-built backend `/health` on 10000 HTTP 200 | | |
| Frontend production-style build | PASS | Temporary shell: `NEXT_PUBLIC_API_URL=https://esevai-api-placeholder.onrender.com`, `NEXT_PUBLIC_SUPABASE_URL=https://example-project.supabase.co`, `NEXT_PUBLIC_SUPABASE_ANON_KEY` placeholder. `npm run build` succeeded. Values were not written to a file | | |
| `npm run start` + security headers | PASS | Port 3000 in use by owner `npm run dev`, so `PORT=3002 npm run start`. `/` and `/login` HTTP 200 with `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`, and CSP. CSP `connect-src` included the placeholder API and Supabase origins plus documented localhost fallbacks. Next.js warned that `next start` is not the standalone entry; pages still served. Vercel does not use `next start`. Docker frontend uses `node server.js`. Standalone kept | | |
| No hard-coded production domain | PASS | `frontend/src` localhost only as `NEXT_PUBLIC_API_URL` development fallback in `api.ts`. Auth `?next=` paths are relative. Login/signup use `router.push` local paths | | |
| Frontend env names | PASS | Only `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`. `.env.example` lists those three with placeholders and a build-time comment | | |
| Test-log template | PASS | `docs/test-log.md`: **37** rows, Result and Notes empty; Bug log 3 empty rows; Known limitations list | | |
| Deployment guide | PASS | `docs/deployment-guide.md` with placeholders `<RENDER_NAME>`, `<VERCEL_NAME>`, `<API_URL>`, `<APP_URL>`. Render Docker Root Directory `backend`. Vercel Root Directory `frontend`. Real config names used (`GEMINI_API_KEY` / `GEMINI_MODEL`; not live Anthropic). `PORT` is not set by the owner. Live smoke uses `E2E_BACKEND_URL` / `E2E_FRONTEND_URL` (the script does not take an email or password) | | |
| Env checklist + README | PASS | `docs/deployment-env-checklist.md` updated (names only). README **Live deployment** section with `<LIVE_FRONTEND_URL>` / `<LIVE_API_URL>` and the private demo-credentials note | | |
| Full-history secret scan | PASS | No real `sk-ant-` keys or long JWTs in history. No `.env` ever tracked. Staged files had no secret-looking values | | |
| No secrets committed | PASS | Two feature commits plus this report. No `.env`, `.env.local`, `.venv`, `node_modules`, `sample-docs`, or binaries | | |
| Two commits pushed | PASS | `dc91e11` Docker support… ; `380e929` Steps 13-14 prep… ; this report is a third commit. Pushed to `origin/main` | | |
| Tree clean after report | PASS | Verified after the report commit | | |
| Render service created and healthy | PENDING-USER | Agent did not open the Render dashboard | Owner follows `docs/deployment-guide.md` step 2 | |
| Vercel project deployed | PENDING-USER | Agent did not open the Vercel dashboard | Owner follows step 3 | |
| Supabase URLs updated | PENDING-USER | Agent did not open Supabase | Owner follows step 4 | |
| Live smoke test all-PASS | PENDING-USER | Script not run against a live URL | Owner follows step 6 after deploy | |
| Manual live tests in test-log.md | PENDING-USER | Result column left empty | Owner fills L1–L5 and the other rows | |
| Phone test on the live site | PENDING-USER | No live URL yet | Owner fills L4 | |

## Overall verdict

AI work: **PASS**; deployment and live tests: **PENDING until the owner deploys**.
