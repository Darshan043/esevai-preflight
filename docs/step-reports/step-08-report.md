# Step 8 verification report

**Date:** 17 November 2026

**Finalized:** 18 November 2026

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
| Pytest counts | PASS | Final run on 18 November 2026: 58 passed, 0 skipped, 1 warning (`StarletteDeprecationWarning`). The two new tests cover labelled names, spaced dates, and form PDFs | | |
| Offline demo | PASS | `scripts/validate_demo.py` printed DEMO PASSED. The good set had no failures. Wrong document, expired date, name mismatch, missing Photo, and blurry photo were all fail | | |
| Frontend replacement tests | PASS | `node --experimental-strip-types --test tests/replacement.test.ts`: 5 passed, 0 failed | | |
| Frontend lint | PASS | `npm run lint` exited 0 | | |
| Frontend build | PASS | `npm run build` exited 0 on Next.js 16.4.6 | | |
| 401 checks | PASS | Validate 401, validation GET 401, `/health` 200, `/` 200, `/applications` 307 to `/login` | | |
| Ownership on new endpoints | PASS | Both routes load the application with the caller's `user_id` and return 404 otherwise. The other-user test returns 404 | | |
| No OCR text, names, or full ID numbers in results | PASS | The privacy test feeds a marker and asserts it is absent from messages, fixes, and details. Name-match details hold codes and scores. ID details hold last 4 digits and a boolean | | |
| Engine is config-driven | PASS | Checks skip when keywords, fields, `id_number_pattern`, or an age limit are absent. No service slug is hard-coded | | |
| Service-role key stays off the frontend | PASS | `frontend/src` has no service-role key | | |
| No secrets committed | PASS | Staged names had no `.env`, `.env.local`, `.venv`, `node_modules`, `sample-docs`, or binary images. The Step 8 diff had no `eyJ`, `sk-ant`, or `service_role` | | |
| Feature commit and push | PASS | `9cbd4ef39e20db1519f3c4f7941c244c53a7fb03` pushed to `origin/main` (`3619304..9cbd4ef`) | | |
| Matching documents and cross-document name validation | PASS | Owner confirmed on 18 November 2026. A matching pair scores as a match. A different name on another processed document fails the shared name check. Details hold document codes and scores | | |
| A blurry photo shows Needs fix | PASS | Owner confirmed blurry-photo detection | | |
| Document validation and status badges | PASS | Owner confirmed the checklist checks and the slot badges | | |
| An empty mandatory slot shows missing | PASS | Owner confirmed missing-document and checklist behaviour | | |
| Results update after upload, replace, and delete | PASS | Owner confirmed replace, delete, and the validation refresh | | |
| Re-running does not create duplicates | PASS | Owner confirmed repeated Re-run checks. The endpoint test also keeps the same saved row count on a second post | | |
| A second user cannot read the first user's results | PASS | Owner confirmed with a second account. The automated test returns 404 | | |
| Badges show Passed, Check advised, and Needs fix | PASS | Owner confirmed all three badges | | |
| Phone-sized screen | PASS | Owner confirmed the checklist at mobile width | | |
| Saved details have no names, OCR sentences, or full ID numbers | PASS | A read of the live `validation_results` rows found flags, field names, and scores only. No names and no 12-digit numbers were in the messages or details | | |
| The wrong document shows "does not look like" | Not a live PASS | This sentence was not one of the nine confirmed live cases. The offline demo and unit tests do fail the wrong document type | The owner did not list this case among the nine | Run it only if that sentence still needs a live look |
| An old-dated document shows expired | Not a live PASS | Seed `max_age_days` is null, so this check stays off. The demo fails a 2020 date when the limit is 90 days | Not part of the nine confirmed cases | Set `validity_days` or `max_age_days` before expecting this warning |
| A dummy ID number shows the checksum warning | Not a live PASS | The seed rows do not set `id_number_pattern`, so the check is skipped. Unit tests cover valid, invalid, and missing | Not part of the nine confirmed cases | Set `rules.id_number_pattern` before expecting this warning |

## OCR follow-up

A one-page form was read as a single paragraph (`--psm 6`), so a two-column table kept the title and dropped the name and date. OCR now uses automatic page segmentation and keeps visual lines, including cells on the same row. `Full Name` is a name label, and dates may have spaces around `-`, `/`, and `.`. A bright white page with a contrast measurement is no longer called bad lighting. A dark page still warns. A blank page still fails.

Known limits: two columns of prose at the same height can be joined into one line. A bright page that is not blank and already has a contrast measurement does not get the lighting warning. The form test draws with `C:\Windows\Fonts\arial.ttf`.

## Replacement synchronization

Replacing a file left the previous badge, quality numbers, and checks on screen until the new read finished. A late validation response could also overwrite a newer one.

The slot now clears that document's checks and the shared checks when replacement starts, hides the old badge and extracted text, and shows only the step in progress: Uploading new document…, Uploading…, Upload complete., Reading document…, Checking document…. New results appear after the backend finishes. Only the latest operation may update the screen. Overlapping validation calls wait and run one at a time.

| Replacement check | Result | Evidence |
| --- | --- | --- |
| Old badge, quality indicators, and OCR text disappear when replacement starts | PASS | Owner confirmed |
| Only the latest upload, read, or validation response updates the screen | PASS | Owner confirmed. The unit test rejects an older epoch |
| New document results appear after processing completes | PASS | Owner confirmed |
| Re-read works | PASS | Owner confirmed |
| Delete works | PASS | Owner confirmed |
| Repeated Re-run checks does not create duplicate results | PASS | Owner confirmed |
| Cancelling replacement restores the previous file and checks | PASS | Owner confirmed |
| An invalid upload is rejected and the previous file remains | PASS | Owner confirmed |

## Verdict

Step 8 is complete. The nine live cases the owner confirmed passed. The date-age check and the ID checksum check stay off until those rule values are set. The "does not look like" sentence was covered by automated tests and was not one of the nine live cases.

The nine live cases and the replacement checks above were confirmed by the owner on 18 November 2026. The steps below are the original checklist.

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
