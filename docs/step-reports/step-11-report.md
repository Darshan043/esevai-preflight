# Step 11 report – admin dashboard

Date: 18 November 2026  
OS: Windows 10, PowerShell

Implementation commit: `c45423b`  
Message: Step 11: admin dashboard – service and checklist management, statistics

## Gate results (Steps 1–10)

GATE PASSED – Steps 1–10 verified.

| Check | Result | Evidence |
| --- | --- | --- |
| B1 step reports 01–10 | PASS | `docs/step-reports/step-01-report.md` … `step-10-report.md` |
| B2 commits for Steps 1–10 | PASS | 1 `9f01613` / `d19f803`; 2 `6cf6300` / `92c0b76`; 3 `279cdbb` / `dd2e2c8`; 4 `0f2aa25` / `1cbef4b`; 5 `9d5cb3d` / `7305173`; 6 `fed1070` / `e1478b6`; 7 `dc09966` / `22f8939`; 8 `9cbd4ef` / `d1e2cd5`; 9 `70c4580` / `37cf07d`; 10 `4586923` / `2f473bd` (plus later `9cf620d` duplicate-key fix) |
| B3 key files | PASS | SQL; `app/auth.py`, `me.py`, `admin.py`, frontend `/admin`; service and application pages; `documents.py`, `UploadSlot.tsx`; processing modules; validation modules + `validation.py` + `docs/validation-rules.md`; AI modules + `ai.py` + `docs/ai-design.md`; `app/report/{scoring,builder}.py`, `report.py`, `/applications/[id]/report`, `docs/readiness-scoring.md` |
| B4 env readiness | PASS | Backend `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`: set. Prompt names `ANTHROPIC_API_KEY` and `CLAUDE_MODEL`: not set (legacy). Live Step 9 names `GEMINI_API_KEY` and `GEMINI_MODEL`: set. Frontend `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `NEXT_PUBLIC_API_URL`: set. Both env files gitignored and untracked. Tracked files: no secret values (only the word `eyJ` in tests asserting absence) |
| B5 OCR tooling | PASS | `tesseract --list-langs` includes `eng` and `tam`. `pdftoppm` version 25.07.0 |
| B6 database | PASS | `community-certificate` exists with 5 active required documents; bucket `documents` exists and is private; six tables respond; at least one profile has role `admin` |
| B7 Step 10 manual tests | PASS | Owner answered yes |
| F1 git clean / origin | PASS | Working tree was clean; local main equalled origin/main at `9cf620d` after fetch |
| F2 backend pytest | PASS | 108 passed before Step 11 code |
| F3 frontend lint/build | PASS | `npm run lint` exit 0; `npm run build` exit 0 |
| F4 curl | PASS | `/` 200, `/services` 200, `/applications` 307 to login, POST report 401, GET `/admin/ping` 401, `/health` 200 |

Fixes applied before Step 11: none. No `Steps 1-10: fixes before Step 11` commit.

## Step 11 checks

| Check | Result | Evidence | Reason if not PASS | Fix |
| --- | --- | --- | --- | --- |
| Gate passed | PASS | Table above | | |
| Config validation | PASS | `backend/app/admin/config_validation.py`: `ServiceInput`, `RequiredDocumentInput`, `Rules` (`extra=forbid`), keyword trim/dedup, regex safety, photo-type cross-field, `validation_errors` | | |
| Clone | PASS | `backend/app/admin/clone.py` always sets `is_active=false`, `is_verified=false`, DRAFT prefix | | |
| Service endpoints | PASS | GET/POST/PUT/DELETE `/admin/services`, duplicate with rollback, slug lock | | |
| Document endpoints | PASS | POST documents, PUT/DELETE `/admin/documents/{id}`, reorder 10/20/30…, code/upload locks | | |
| Stats endpoints | PASS | GET `/admin/stats?days=`, GET `/admin/applications` pagination; footnote in code and UI | | |
| Auth on every admin endpoint | PASS | Tests: no token 401, citizen 403 for ping, services CRUD, documents, reorder, stats, applications | | |
| Locks | PASS | Slug locked after applications; delete service with applications 409; code locked after uploads; delete document with uploads 409 | | |
| pytest counts | PASS | **120 passed** (108 from Steps 2–10 plus 12 admin tests). Autouse fixture still refuses a real Gemini client. Different-service engine test uses dummy `income-certificate` / `salary_slip` through `validate_application` and `build_report`; inactive required docs are skipped | | |
| Demo results | PASS | `scripts/admin_demo.py`: dummy second service valid and inactive/unverified; Community Certificate clone is a draft with 2 documents; five bad inputs print field errors (bad slug, nested regex, brightness min>max, unknown rule key, photo-type name matching); sample stats average 75.0, activity fills 2026-11-17 with 0, anonymised `User #fc9529` | | |
| lint | PASS | `npm run lint` exit 0 | | |
| build | PASS | `npm run build` exit 0 (Next.js 16.4.6). Admin routes listed | | |
| 401 checks | PASS | Unauthenticated: GET `/admin/services` 401, GET `/admin/stats` 401, POST `/admin/services` 401, PUT `/admin/documents/<uuid>` 401, DELETE `/admin/services/<uuid>` 401, `/health` 200. Frontend logged out: `/admin`, `/admin/services`, `/admin/services/new` 307 to `/login?next=…`; `/` 200 | | |
| require_admin on every admin endpoint | PASS | `admin.py`, `admin_config.py`, `admin_stats.py` all use `Depends(require_admin)` | | |
| Strict payload validation | PASS | Pydantic `extra=forbid`; 422 returns `{field,message}` list | | |
| Regex safety | PASS | Nested quantifiers rejected; more than two quantifier groups rejected; 50 ms timing on a 200-character sample | | |
| Privacy review | PASS | Stats select only id/role/score/summary/dates; `anonymise_user_id` SHA-256[:6]; tests assert marker email, OCR, path, and full user id never appear | | |
| Service-role key not in frontend | PASS | Grep of `/frontend` found no service-role, `eyJ`, or `sk-ant` | | |
| Delete/slug/code locks on server | PASS | Enforced in `admin_config.py`, not only the UI | | |
| No secrets committed | PASS | Staged names had no `.env`, `.env.local`, `.venv`, `node_modules`, `sample-docs`, or binary images. Diff had `SUPABASE_SERVICE_ROLE_KEY` only as the env **name** in README | | |
| Commit and push | PASS | `c45423b` on origin/main | | |
| Tree clean (implementation) | PASS | After the implementation commit, only this report was still uncommitted | | |
| Citizen cannot open `/admin` or call admin endpoints | PENDING-USER | Proxy sends logged-out visitors to `/login`. Server gate renders Access denied for non-admins. APIs return 401/403 | Owner must confirm with a citizen account | |
| Admin overview shows sensible numbers | PENDING-USER | Overview cards and tables read `/admin/stats` | Sign in as admin | |
| Create "Income Certificate (Demo)" with 3 documents | PENDING-USER | Dashboard forms POST `/admin/services` and `/documents` | Create while inactive | |
| Inactive service hidden; appears after activation | PENDING-USER | `/services` filters `is_active=true`; start-check refuses inactive | Activate after the draft looks right | |
| Citizen full check on the new service, no code change | PENDING-USER | Engine reads `required_documents` rows | Run upload → validate → report | |
| Duplicate creates inactive draft | PENDING-USER | Clone API + Duplicate modal | | |
| Invalid rules rejected beside the field | PENDING-USER | 422 field/message list shown on the form | Try a bad regex and brightness min>max | |
| Slug/code locks and unused-only delete | PENDING-USER | 409 messages from the server | | |
| Deactivate stops new checks; old apps still open | PENDING-USER | `startNewCheck` redirects `?error=inactive`; existing `/applications/[id]` still loads | | |
| Reorder changes citizen checklist order | PENDING-USER | Saved `sort_order` 10, 20, 30… | | |
| Stats show no emails, names, or document content | PENDING-USER | Aggregate columns and `User #` labels only | | |
| Works at phone width | PENDING-USER | Mobile-first layout, wrapping tables with overflow | | |

## Overall verdict

AI work: PASS; live admin tests: PENDING until the owner tests.

Do not start Step 12 until the owner has walked through the list below.

## Manual test steps for the owner

1. Start both servers (commands below). Sign in as a **citizen**. Confirm `/admin` shows Access denied and that calling `/admin/stats` with the citizen token is 403.
2. Sign in as an **admin**. Open `/admin`. Confirm the overview cards, label bar, top failure reasons, per-service table, daily bars, recent-checks table, and the footnote about current data.
3. Open `/admin/services` → **New service**. Create **Income Certificate (Demo)** with slug `income-certificate-demo`, leave Active and Verified off, and add three documents (for example Photo, Salary slip, Address proof) with keywords and rules. Confirm it does **not** appear on `/services` while inactive.
4. Activate the service. Confirm it appears at `/services` and `/services/income-certificate-demo`.
5. As a citizen, start a check on Income Certificate (Demo), upload sample files, run checks, and generate a report. No code change should be needed.
6. As admin, **Duplicate** Community Certificate into a new slug. Confirm the copy is Draft, inactive, and has the same documents.
7. Edit a document: set ID pattern to `(a+)+` and brightness max below min. Confirm the form shows a clear error beside the field and does not save.
8. Confirm a used service cannot be deleted (tooltip / 409) and that its slug cannot change. Confirm a document with uploads cannot change code or be deleted.
9. Deactivate Income Certificate (Demo). Confirm `/services` hides it and **Start a new check** is refused, but an old application still opens.
10. Reorder documents on an active service. Confirm the citizen checklist order matches.
11. On Overview, confirm there are no emails, holder names, OCR text, or file paths. Narrow the browser to phone width.

### Start the servers (Windows PowerShell)

```powershell
cd D:\esevai-preflight\backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

```powershell
cd D:\esevai-preflight\frontend
npm run dev
```

Backend: http://127.0.0.1:8000/health  
Frontend: http://localhost:3000
