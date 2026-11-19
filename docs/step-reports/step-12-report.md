# Step 12 report – integration and error handling

Date: 19 November 2026  
OS: Windows 10, PowerShell

Implementation commit: `8f5a421`  
Message: Step 12: integration and error handling – consistent errors, safe logging, production checks, rate limits, retention, e2e smoke test

## Gate results (Steps 1–11)

GATE PASSED – Steps 1–11 verified. Owner answered **yes** on Step 11 manual tests (B7).

| Check | Result | Evidence |
| --- | --- | --- |
| B1 step reports 01–11 | PASS | `docs/step-reports/step-01-report.md` … `step-11-report.md` |
| B2 commits for Steps 1–11 | PASS | 1 `9f01613`; 2 `6cf6300`; 3 `279cdbb`; 4 `0f2aa25`; 5 `9d5cb3d`; 6 `fed1070`; 7 `dc09966`; 8 `9cbd4ef`; 9 `70c4580`; 10 `4586923`; 11 `c45423b` (plus later admin/UI/AI commits) |
| B3 key files | PASS | SQL; auth/pages/upload/OCR/validation/AI/report/admin modules; `docs/admin-guide.md` |
| B4 env readiness | PASS | Backend `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`: set. Prompt names `ANTHROPIC_API_KEY` and `CLAUDE_MODEL`: not set (legacy). Live AI names `GEMINI_API_KEY` and `GEMINI_MODEL`: set. Frontend public vars set. Env files gitignored |
| B5 OCR tooling | PASS | `tesseract` `eng`+`tam`; `pdftoppm` 25.07.0 |
| B6 database | PASS | `community-certificate` with 5 active required documents; bucket `documents` private; six tables; at least one admin |
| B7 Step 11 manual tests | PASS | Owner answered yes |
| F1 git clean / origin | PASS | Working tree was clean; local main equalled origin/main at `1c926e5` |
| F2 backend pytest | PASS | 120 passed before Step 12 code |
| F3 frontend lint/build | PASS | lint exit 0; build exit 0 |
| F4 curl | PASS | `/` 200, `/services` 200, `/applications` → login, `/admin/stats` 401, `/health` 200 |

Fixes applied before Step 12: none. No `Steps 1-11: fixes before Step 12` commit.

## Step 12 checks

| Check | Result | Evidence | Reason if not PASS | Fix |
| --- | --- | --- | --- | --- |
| Gate passed | PASS | Table above | | |
| Unified error envelope | PASS | `GET /me` without a token: `401` `{"error":{"code":"UNAUTHORIZED","message":"A login token is required.","request_id":"…"}}` plus `X-Request-ID`. Tests updated via `api_message()` | | |
| Request IDs | PASS | Middleware accepts a safe incoming id; unsafe ids are replaced. Header present on `/health` and `/me` | | |
| Safe logging | PASS | One-line request logs; JWT / `sk-ant-` / 12–16 digit numbers redacted. OCR logs use `request_id`, not document ids | | |
| Production config | PASS | Dummy production settings refuse with names only: `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `GEMINI_API_KEY`, `GEMINI_MODEL`, `ALLOWED_ORIGINS`. Gemini is the live AI check when `AI_ENABLED` | | |
| `/health/ready` | PASS | Live: `200` `{"status":"ok","checks":{"database":"ok","storage":"ok","ocr":"ok","tamil_ocr":"yes"}}` | | |
| `/docs` in production | PASS | `TestClient(create_app())` with `ENVIRONMENT=production`: `/docs` and `/openapi.json` 404. Development `/docs` still 200 | | |
| Security headers | PASS | Backend: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`. Frontend `next start -p 3001` and `next dev`: CSP, `nosniff`, `DENY`, `no-referrer`, `Permissions-Policy` | | |
| Rate limits | PASS | In-memory sliding window. `/health/ready` with limit 1 returns 429 + `Retry-After`. Uploads/process/validate-report/admin writes use the signed-in user id | | |
| Body size | PASS | JSON over 1 MB and uploads over `MAX_UPLOAD_MB+1` return 413 | | |
| Retention dry-run | PASS | `scripts/cleanup_old_data.py` printed `applications=0 files=0`. Storage-before-row and storage-failure-leaves-row covered in pytest. `--apply` was not run | | |
| Frontend mapper / timeout / GET retry | PASS | `frontend/src/lib/api-errors.ts` reads `error.message` then falls back to `detail`. 30s default, 60s process/AI. GET retries once on network error | | |
| Error/loading/offline | PASS | `error.tsx`, `global-error.tsx`, `not-found.tsx`, `loading.tsx`, `OfflineBanner` on the root layout | | |
| Auto-resume OCR | PASS | `shouldAutoResume` for `uploaded` and stalled `processing` (≥ 2 minutes). `UploadSlot` starts a read after reload | | |
| Double-submit | PASS | Login, signup, upload, explain, report, admin save, retention buttons ignore a second click while busy | | |
| Admin retention UI | PASS | Overview **Data retention** card: dry-run default, confirm before delete, counts only | | |
| e2e smoke | PASS | `py_compile` + `scripts/e2e_smoke.py --selftest` passed. Live e2e was not run by the agent | | |
| pytest | PASS | **143 passed**. Autouse still refuses a real Gemini client. Rate limiter reset between tests | | |
| frontend tests | PASS | 35 passed (`node --experimental-strip-types --test`) | | |
| lint | PASS | `npm run lint` exit 0 | | |
| build | PASS | `npm run build` exit 0 (Next.js 16.4.6) | | |
| Privacy review | PASS | Error bodies and request logs do not include OCR text, names, emails, storage paths, or signed URLs. Cleanup prints counts only | | |
| Service-role key not in frontend | PASS | Frontend grep found no service-role, `eyJ`, or `sk-ant` | | |
| No secrets committed | PASS | Staged names had no `.env`, `.env.local`, `.venv`, `node_modules`, or `sample-docs`. Diff `eyJ`/`sk-ant` only in redaction tests | | |
| Commit and push | PASS | `8f5a421` on origin/main | | |
| Live e2e against the real app | PENDING-USER | Script is `backend/scripts/e2e_smoke.py`. Agent ran `--selftest` only | Owner runs without `--selftest` while both servers are up | |
| 429 after many uploads | PENDING-USER | Limit is 30/hour per signed-in user | Upload more than 30 files in one hour | |
| Retention apply | PENDING-USER | Admin confirm + `--apply` delete storage then rows | Only after reviewing dry-run counts | |
| Production `/docs` 404 on Render | PENDING-USER | Local production TestClient 404 | Confirm after Step 14 deploy | |

## Overall verdict

Integration work: PASS; live owner e2e and retention apply: PENDING until the owner runs them.

Do not start Step 13 (Docker) until the owner has walked through the list below.

## Manual test steps for the owner

1. With both servers running, from `backend` run `.\.venv\Scripts\python.exe scripts\e2e_smoke.py`. It must not create rows. Confirm `/health`, `/health/ready`, unauthenticated `/me` error envelope, and the homepage.
2. Sign in as a citizen. Upload a file, turn the network off, confirm the offline banner, then reconnect.
3. Upload a file and reload the checklist while status is still **Uploaded**. Confirm reading resumes by itself.
4. Open a missing URL such as `/this-page-is-missing` and confirm the not-found page.
5. Sign in as an admin. Open `/admin`. Use **Preview old applications**. Confirm counts only, no names or paths. Do not click delete unless you mean it.
6. From `backend` run `.\.venv\Scripts\python.exe scripts\cleanup_old_data.py` (dry-run). Do not pass `--apply` unless you intend to delete old applications.

### Start the servers

```powershell
cd D:\esevai-preflight\backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

```powershell
cd D:\esevai-preflight\frontend
npm run dev
```
