# Step 8 verification report

**Date:** 17 November 2026  
**OS:** Windows 10.0.26200, PowerShell  
**Title:** Step 8 – document validation engine

## Gate

GATE PASSED – Steps 1–7 verified. No Steps 1–7 code fixes were required.

The owner answered yes: manual Step 7 tests passed.

| Check | Result | Evidence |
| --- | --- | --- |
| B1 step reports | PASS | `docs/step-reports/step-01-report.md` through `step-07-report.md` exist |
| B2 step commits | PASS | Step 1 `9f01613`, Step 2 `6cf6300`, Step 3 `279cdbb`, Step 4 `0f2aa25`, Step 5 `9d5cb3d`, Step 6 `fed1070`, Step 7 `dc09966` |
| B3 key files | PASS | Schema, RLS, storage, seed, auth, me, admin, service and checklist pages, documents router, UploadSlot, processing modules, and `scripts/ocr_demo.py` |
| B4 env | PASS | Backend `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` are set. Frontend `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, and `NEXT_PUBLIC_API_URL` are set. Both env files are gitignored. Tracked secret-looking strings were only the words in older reports, tests, and one package-lock integrity hash |
| B5 OCR tools | PASS | Configured Tesseract lists `eng` and `tam`. `pdftoppm` version 25.07.0 |
| B6 database | PASS | `community-certificate` has 5 active required documents. Bucket `documents` exists and is private. All six tables responded |
| B7 manual Step 7 | PASS | Owner answered yes |
| F1 git sync | PASS | Working tree was clean and `main` matched `origin/main` at `3619304` after fetch |
| F2 pytest | PASS | 45 passed before Step 8 code |
| F3 lint and build | PASS | `npm run lint` and `npm run build` exited 0 |
| F4 logged-out routes | PASS | `/` 200, `/services` 200, `/applications` 307 to `/login`, process without a token 401, `/health` 200 |

Required-document summary from the live database:

| Code | Keywords | Fields | Validity days | Rule keys |
| --- | --- | --- | --- | --- |
| applicant_photo | 0 | none | none | check_name_match, fields_are_draft, max_brightness, min_blur_score, min_brightness, min_height, min_width |
| address_proof | 3 | name, date | none | check_name_match, fields_are_draft, max_age_days, max_brightness, min_blur_score, min_brightness, min_height, min_width |
| parent_or_sibling_community_certificate | 5 | name, date | none | check_name_match, fields_are_draft, max_age_days, max_brightness, min_blur_score, min_brightness, min_height, min_width |
| self_declaration | 4 | name, date | none | check_name_match, fields_are_draft, max_age_days, max_brightness, min_blur_score, min_brightness, min_height, min_width |
| dnc_certificate | 3 | name, date | none | check_name_match, discrepancy_unresolved, fields_are_draft, max_age_days, max_brightness, min_blur_score, min_brightness, min_height, min_width |

`max_age_days` is null on those rows, so the age check stays off until a number is set. The photo row has no keywords and no required fields, so it gets image checks only.

## Checks

| Check | Result | Evidence | Reason if not PASS | Fix |
| --- | --- | --- | --- | --- |
| Gate passed | PASS | Table above. No "Steps 1-7: fixes before Step 8" commit | | |
| Verhoeff and id_checks | PASS | `test_id_checksum_reports_last4_only` builds the check digit in the test. One changed digit is invalid. The result holds only the last 4 digits. The pipeline stores `id_checks` before masking | | |
| Engine modules | PASS | `models.py`, `defaults.py`, `text_extract.py`, `checks.py`, `cross_checks.py`, `engine.py` | | |
| Endpoints | PASS | `POST /applications/{id}/validate` and `GET /applications/{id}/validation`. Replace, delete, and re-read also clear application-level results | | |
| Pytest counts | PASS | 56 passed, 0 skipped, 1 warning (`StarletteDeprecationWarning`). Engine tests were not skipped | | |
| Offline demo | PASS | `scripts/validate_demo.py` printed DEMO PASSED. The good set had no failures. Wrong document, expired date, name mismatch, missing Photo, and blurry photo were all fail | | |
| Frontend lint | PASS | `npm run lint` exited 0 | | |
| Frontend build | PASS | `npm run build` exited 0 on Next.js 16.4.6 | | |
| 401 checks | PASS | Validate 401, validation GET 401, `/health` 200, `/` 200, `/applications` 307 to `/login` | | |
| Ownership on new endpoints | PASS | Both routes load the application with the caller's `user_id` and return 404 otherwise. The other-user test returns 404 | | |
| No OCR text, names, or full ID numbers in results | PASS | The privacy test feeds a marker and asserts it is absent from messages, fixes, and details. Name-match details hold codes and scores. ID details hold last 4 digits and a boolean | | |
| Engine is config-driven | PASS | Checks skip when keywords, fields, `id_number_pattern`, or an age limit are absent. No service slug is hard-coded | | |
| Service-role key stays off the frontend | PASS | `frontend/src` has no service-role key | | |
| No secrets committed | PASS | Staged names had no `.env`, `.env.local`, `.venv`, `node_modules`, `sample-docs`, or binary images. The Step 8 diff had no `eyJ`, `sk-ant`, or `service_role` | | |
| Feature commit and push | PASS | `9cbd4ef39e20db1519f3c4f7941c244c53a7fb03` pushed to `origin/main` (`3619304..9cbd4ef`) | | |
| A good document set shows Passed or only minor warnings | PENDING-USER | Needs a signed-in checklist | The offline demo good set passed | Upload a clear matching set and press Re-run checks |
| A blurry photo shows Needs fix | PENDING-USER | Needs a blurry upload | The demo flags blur as fail | Upload a blurry photo |
| The wrong document shows "does not look like" | PENDING-USER | Needs the wrong file in a slot | The demo fails document type | Put an unrelated page in Address Proof |
| An old-dated document shows expired | PENDING-USER | Needs a date limit on the row | Seed `max_age_days` is null, so this check is off until a number is saved. The demo fails a 2020 date when the limit is 90 days | Set `validity_days` or `max_age_days`, then upload an old document |
| Two different names show the name-mismatch problem | PENDING-USER | Needs two processed files | The demo fails Anitha Kumar against Ravi Sharma | Use two documents with clearly different names |
| An empty mandatory slot shows missing | PENDING-USER | Needs an empty slot | The demo fails a missing Photo | Leave Photo empty and press Re-run checks |
| A dummy ID number shows the checksum warning | PENDING-USER | Needs `id_number_pattern` on that row | The seed rows do not set `id_number_pattern`, so the check is skipped until it is set. Unit tests cover valid, invalid, and missing | Set `rules.id_number_pattern` and upload a page with a dummy 12-digit number |
| Results update after upload, replace, and delete | PENDING-USER | Needs the live checklist | The page calls validate after read, replace, and delete | Upload, replace, and delete one file |
| Supabase rows have no names, text, or full numbers in details | PENDING-USER | Do not create a row from this session | Details are codes, numbers, booleans, and last-4 digits | Inspect `validation_results.details` |
| Re-running does not create duplicates | PENDING-USER | Needs two live runs | The mocked endpoint test replaces old rows | Press Re-run checks twice |
| A second user cannot read the first user's results | PENDING-USER | Needs two accounts | The automated test returns 404 | Sign in as the other account and open the same URL |
| Badges show Passed, Check advised, and Needs fix | PENDING-USER | Needs the checklist | `slotStatus` maps fail, warning-only, and all-pass | Compare one of each |
| Phone-sized screen | PENDING-USER | Needs the checklist on a phone | Controls stack in one column | Open a checklist on a phone |

## Verdict

AI work: PASS; live validation tests: PENDING until the owner tests.

## Manual test steps for the owner

1. Start the backend and frontend with the commands below. If they are already running, leave them running.
2. Sign in and open a draft Community Certificate checklist.
3. Upload a clear address proof and a self-declaration that show the same name and a recent date. Press **Re-run checks**. Passed checks stay collapsed. The badges should say Passed, or Check advised if only warnings remain.
4. Upload a blurry photo in the Photo slot. The badge should say Needs fix, and the photo-quality check should say the photo is too blurry.
5. Put an unrelated page in the Address Proof slot. The check should say it does not look like that document.
6. To try the date check, set `validity_days` or `rules.max_age_days` on that document row, then upload a page with an old date. The check should say the document is too old. The seeded rows currently leave this limit empty, so the check stays off until you set a number.
7. Upload two documents whose names are clearly different. The top of the checklist should say the names do not match. The saved details should contain document codes and a score, not the names.
8. Leave the Photo slot empty and press **Re-run checks**. The top section should say Photo is missing.
9. To try the ID checksum, set `rules.id_number_pattern` on a document row and upload a page with a dummy 12-digit number. An invalid checksum should warn, and the details should show only the last 4 digits.
10. Replace a file, then delete a file. The checks should refresh on their own.
11. In Supabase, open `validation_results` and confirm `details` has no names, OCR sentences, or full ID numbers.
12. Press **Re-run checks** again and confirm the row count does not double.
13. Sign in as a second user and confirm that user cannot open the first user's validation URL.
14. Confirm the badges say Passed, Check advised, or Needs fix with both an icon and those words.
15. Repeat one checklist on a phone-width screen. Buttons stay tappable and the check list scrolls.

### Start the servers (Windows PowerShell)

```powershell
cd D:\esevai-preflight\backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000
```

```powershell
cd D:\esevai-preflight\frontend
npm run dev
```

Offline check, with no database:

```powershell
cd D:\esevai-preflight\backend
.\.venv\Scripts\python.exe scripts\validate_demo.py
```
