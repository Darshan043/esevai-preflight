# Step 10 report – readiness report

Date: 18 November 2026  
OS: Windows 10, PowerShell

Implementation commit: `4586923`  
Message: Step 10: readiness report – score, next steps, printable report page

## Gate results (Steps 1–9)

GATE PASSED – Steps 1–9 verified.

| Check | Result | Evidence |
| --- | --- | --- |
| B1 step reports 01–09 | PASS | `docs/step-reports/step-01-report.md` … `step-09-report.md` |
| B2 commits for Steps 1–9 | PASS | 1 `9f01613` / `d19f803`; 2 `6cf6300` / `92c0b76`; 3 `279cdbb` / `dd2e2c8`; 4 `0f2aa25` / `1cbef4b`; 5 `9d5cb3d` / `7305173`; 6 `fed1070` / `e1478b6`; 7 `dc09966` / `22f8939`; 8 `9cbd4ef` / `d1e2cd5`; 9 `70c4580` / `37cf07d` |
| B3 key files | PASS | SQL, `app/auth.py`, `me.py`, `admin.py`, frontend service and application pages, `documents.py`, `UploadSlot.tsx`, processing six modules, validation six modules + router + `docs/validation-rules.md`, AI four modules + `routers/ai.py` + `docs/ai-design.md` |
| B4 env readiness | PASS | Backend `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`: set. Prompt names `ANTHROPIC_API_KEY` and `CLAUDE_MODEL`: not set (legacy). Live Step 9 names `GEMINI_API_KEY` and `GEMINI_MODEL`: set. Frontend `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `NEXT_PUBLIC_API_URL`: set. Both env files gitignored and untracked. Tracked files: no secret values (only the words `eyJ` in tests asserting absence) |
| B5 OCR tooling | PASS | `tesseract --list-langs` includes `eng` and `tam`. `pdftoppm` version 25.07.0 |
| B6 database | PASS | Uncommitted read-only check: `community-certificate` exists with 5 active required documents; bucket `documents` exists and `public=false`; six tables respond |
| B7 Step 9 manual tests | PASS | Owner answered yes |
| F1 git clean / origin | PASS after push | Working tree was clean; local main was 2 commits ahead (`97388a3`, `797cb5d`). Those existing Step 9 follow-up commits were pushed. No extra “Steps 1-9: fixes” commit |
| F2 backend pytest | PASS | 87 passed before Step 10 code |
| F3 frontend lint/build | PASS | `npm run lint` exit 0; `npm run build` exit 0 |
| F4 curl | PASS | `/` 200, `/services` 200, `/applications` 307 to login, POST validate 401, POST explain 401, `/health` 200 |

Fixes applied before Step 10: none beyond pushing the two already-made Step 9 follow-up commits so local main equalled origin/main.

## Step 10 checks

| Check | Result | Evidence | Reason if not PASS | Fix |
| --- | --- | --- | --- | --- |
| Gate passed | PASS | Table above | | |
| Scoring module | PASS | `backend/app/report/scoring.py` constants and pure functions | | |
| Builder | PASS | `backend/app/report/builder.py` next steps, sanitiser, carry list | | |
| Endpoints | PASS | `POST`/`GET /applications/{id}/report` in `app/routers/report.py`; registered in `main.py` | | |
| Stale-report hygiene | PASS | Upload, replace, delete, and re-process call `_after_document_change`; tests cover replace/delete/process | | |
| pytest counts | PASS | **108 passed** (`87` from Steps 2–9 plus `21` report tests). Autouse fixture still refuses a real Gemini client | | |
| Demo results | PASS | `scripts/report_demo.py`: GOOD 100 ready; MIXED 83 almost_ready; BAD 50 not_ready with missing ID first; EMPTY-OPTIONAL 100 ready | | |
| lint | PASS | `npm run lint` exit 0 | | |
| build | PASS | `npm run build` includes `/applications/[id]/report` | | |
| 401 checks | PASS | Logged-out POST report 401, GET report 401, `/health` 200. Frontend `/` 200; `/applications` and `/applications/<uuid>/report` 307 to `/login` | | |
| Privacy review | PASS | Owner check on both endpoints; `_public_report` allow-list; sanitiser strips 12/16-digit numbers and URLs; scoring ignores AI; stale report cleared on document change; `frontend/src` has no service-role key | | |
| No secrets committed | PASS | Staged names had no `.env`, `.env.local`, `.venv`, `node_modules`, `sample-docs`, or binary images. Diff had `eyJ` only as `assert "eyJ" not in response.text` | | |
| Commit and push | PASS | `4586923` pushed to `origin/main` | | |
| Tree clean (after implementation commit) | PASS | `git status -sb` was `main...origin/main` | | |
| Good set → Ready to apply | PENDING-USER | Demo GOOD is ready/100. Live UI not exercised by the agent | Needs a signed-in browser pass | Owner: upload a clean set, generate the report |
| Mixed set → Almost ready | PENDING-USER | Demo MIXED is almost_ready/83 | Live UI | Owner: generate with warnings only |
| Failed or missing mandatory → Not ready, listed first | PENDING-USER | Demo BAD next step 1 is `Get or upload: ID card` | Live UI | Owner: leave a mandatory slot empty |
| Generate blocked while files are still being read | PENDING-USER | Button disables when status is `uploaded` or `processing`; API returns 409 | Live UI | Owner: click generate before OCR finishes |
| Replace makes report stale | PENDING-USER | Backend clears `summary.report`, sets `draft` and null score; page copy is “Your documents changed after this report – generate it again” | Live UI | Owner: replace a file after generating |
| Report page content | PENDING-USER | Page implements score, counts, next steps, documents, carry list, disclaimer | Live UI | Owner: open `/applications/[id]/report` |
| Tamil names with language toggle | PENDING-USER | `pickName` uses `name_ta` when the language cookie is Tamil | Live UI | Owner: switch to தமிழ் |
| Explain issues on the report page | PENDING-USER | Reuses `POST /applications/{id}/explain` | Live UI / Gemini | Owner: click the button |
| Print / Save as PDF | PENDING-USER | `window.print()`; header/footer/buttons `print:hidden`; print stylesheet | Live print dialog | Owner: print to PDF |
| My applications score badge and View report | PENDING-USER | List shows score, label badge, and View report when `summary.report` exists | Live UI | Owner: open `/applications` |
| Supabase row has score, `checked`, no names/text/full numbers | PENDING-USER | POST writes `readiness_score`, `status='checked'`, `summary.report` | Live Dashboard | Owner: inspect the applications row |
| Second user blocked | PENDING-USER | Unknown/foreign ids return 404; proxy sends logged-out visitors to login | Live second account | Owner: paste the report URL while signed in as someone else |
| Phone width | PENDING-USER | Mobile-first layout, 44px tap targets | Live phone or narrow window | Owner: resize below `sm` |

## Overall verdict

AI work: **PASS**; live report tests: **PENDING until the owner tests**.

## Manual test steps for the owner

1. Start both servers with the commands below.
2. Sign in and open a Community Certificate application with at least one processed document.
3. Confirm **Generate readiness report** is disabled while a file is still `uploaded` or `processing`.
4. When reading has finished, generate the report. Confirm you land on `/applications/[id]/report` and see the score, label (text + colour), counts, next steps, documents, carry list, and disclaimer.
5. Use a **good** set (all checks pass) and confirm **Ready to apply** with a high score.
6. Use a **mixed** set (warnings only) and confirm **Almost ready**.
7. Use a set with a failed document or a missing mandatory slot and confirm **Not ready yet**, with that item first in **What to do next**.
8. Switch the language toggle to Tamil and confirm document names use `name_ta` where present.
9. Click **Explain issues in simple words** and confirm the “AI-written advice” block.
10. Click **Print / Save as PDF** and save a PDF. Confirm the menu, buttons, and toggles are hidden.
11. Replace a document, reopen the report URL, and confirm “Your documents changed after this report – generate it again”.
12. Open **My applications** and confirm the score badge and **View report**. Open the Dashboard and confirm the latest score.
13. In the Supabase Table Editor, open that `applications` row: `readiness_score` is set, `status` is `checked`, and `summary.report` has no names, OCR text, or full ID numbers.
14. Sign in as a second user (or a private window) and open the first user’s report URL. You should be blocked (login or not found).
15. Repeat the report page at phone width.

## Commands to start both servers (Windows PowerShell)

Backend:

```powershell
cd D:\esevai-preflight\backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

Frontend (a second terminal):

```powershell
cd D:\esevai-preflight\frontend
npm run dev
```

Open http://localhost:3000 while the API is on http://localhost:8000.

Do not start Step 11 until the owner has tried the live report.
