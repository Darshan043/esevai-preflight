# Step 7 verification report

**Date:** 17 November 2026  
**OS:** Windows 10.0.26200, PowerShell  
**Title:** Step 7 – image processing and OCR

## Gate

GATE PASSED – Step 6 verified. No Step 6 code fixes were required.

| Check | Result | Evidence |
| --- | --- | --- |
| B1 required files | PASS | `documents.py`, `supabase_client.py`, `test_documents.py`, `UploadSlot.tsx`, `docs/step-reports/step-06-report.md` exist |
| B2 Step 6 commits | PASS | `fed1070` and `e1478b6` are in `git log` |
| B3 env and secrets | PASS | Both Supabase backend names and all three frontend names are set. `backend/.env` and `frontend/.env.local` are gitignored. Tracked secret-looking strings were only the words in report docs and one package-lock integrity hash |
| B4 OCR tools | PASS | Tesseract 5.4.0.20240606 lists `eng` and `tam`. Poppler `pdftoppm` 25.07.0 |
| B5 database | PASS | Service `community-certificate` exists. Bucket `documents` exists and is private |
| B6 manual Step 6 | PASS | Owner confirmed uploads, rejects, preview, replace, delete, storage, the second user, and application deletion |
| F1 git sync | PASS | Working tree was clean and `main` matched `origin/main` at `9eb40f7` |
| F2 pytest | PASS | 28 passed before Step 7 code |
| F3 lint and build | PASS | `npm run lint` and `npm run build` exited 0 |
| F4 logged-out routes | PASS | `/` 200, `/services` 200, `/applications` 307 to `/login`, upload without a token 401 |

## Checks

| Check | Result | Evidence | Reason if not PASS | Fix |
| --- | --- | --- | --- | --- |
| Gate passed | PASS | Table above. No "Step 6: fixes before Step 7" commit | | |
| Loader | PASS | PNG, JPEG, and a 3-page PDF load. The PDF reports 3 pages and keeps 2. Garbage bytes and an over-pixel image raise `DocumentUnreadableError` | | |
| Quality | PASS | Sharp blur score is higher than a Gaussian blur. A dark image is less bright. A rotated mark has a non-zero tilt. A white image is blank. Width and height match | | |
| Preprocess | PASS | `prepare_for_ocr` returns grayscale. Thresholding stays an optional helper | | |
| OCR module | PASS | `test_ocr_reads_clear_english_and_blank_page` ran and was not skipped. It read HELLO and CITIZEN. A blank image returned empty text | | |
| Masking | PASS | Spaced, plain, hyphenated, Tamil-digit, and 16-digit numbers keep only the last 4. A 10-digit phone, `12/05/2003`, and PIN `600001` stay unchanged. Suffixes are 4 digits | | |
| Pipeline | PASS | A generated image of `1234 5678 9012` returned `XXXX XXXX 9012`. The raw groups were absent from the result and from the log | | |
| Endpoints | PASS | No token is 401. Another user is 404. Success stores metrics, masked text, `extracted_fields {}`, and status `processed`. A pipeline crash stores `failed` and a friendly error with no raw text. A fresh `processing` row is 409. A 10-minute-old `processing` row can run again. Responses omit `storage_path` | | |
| Pytest counts | PASS | 44 passed, 0 skipped, after the OCR tests. The two Tesseract tests ran | | |
| Offline demo | PASS | Clear image blur score 1204.69 versus blurred copy 1.01. Both read `HELLO CITIZEN Aadhaar XXXX XXXX 9012` and did not contain `1234 5678`. A generated PDF did the same. The temp folder was deleted | | |
| Frontend lint | PASS | `npm run lint` exited 0 | | |
| Frontend build | PASS | `npm run build` exited 0 on Next.js 16.4.6 | | |
| Unauthenticated curls | PASS | `POST /documents/{id}/process` 401, `GET /documents/{id}/result` 401, `/health` 200, `/` 200, `/applications` 307 to `/login` | | |
| Masking proven | PASS | Unit tests, the pipeline test, the endpoint test, and the offline demo all hide `1234 5678` | | |
| Ownership on new endpoints | PASS | Both routes load the row with the caller's `user_id` and return 404 otherwise | | |
| OCR text not logged or returned raw | PASS | Logs record counts, status, and duration. The endpoint masks again before save. Log capture did not contain the sample text | | |
| Only masked text stored | PASS | Success update writes `ocr_text_masked` after `mask_sensitive`. Failure stores `null` | | |
| Temp files removed | PASS | PDF conversion uses a temp folder removed in `finally`. The demo temp folder was deleted | | |
| `storage_path` never returned | PASS | Result bodies are built from an explicit field list. Tests assert the path is absent | | |
| Service-role key stays off the frontend | PASS | `frontend/src` has no service-role key | | |
| Pixel and page limits | PASS | Images over `OCR_MAX_PIXELS` are rejected. PDFs keep at most `OCR_MAX_PDF_PAGES` | | |
| Work stays off the event loop | PASS | Download and OCR run through `run_in_threadpool` | | |
| No secrets or sample files committed | PASS | Staged diff had no `eyJ`, `sk-ant`, `sb_secret`, or `service_role`. `.env`, `.env.local`, `.venv`, `node_modules`, `sample-docs`, and binary test images were not staged | | |
| Feature commit and push | PASS | `dc09966` pushed to `origin/main` (`9eb40f7..dc09966`) | | |
| Tree clean after the feature commit | PASS | `git status` was clean after `dc09966` | | |
| A clear English document is read correctly | PENDING-USER | Needs a signed-in upload | The offline demo read HELLO CITIZEN. The live checklist still needs the owner | Upload a clear JPG and open the text panel |
| A blurry photo shows lower Sharpness | PENDING-USER | Needs two live photos | The demo scored 1204.69 versus 1.01 | Compare the Sharpness rows |
| A dark photo shows low Brightness | PENDING-USER | Needs a dark live photo | Unit test compared brightness 20 versus 230 | Compare the Brightness rows |
| A text PDF is processed | PENDING-USER | Needs a signed-in PDF | The demo PDF returned the masked sentence | Upload a text PDF |
| A Tamil document is read | PENDING-USER | Optional | `tam` is installed. No Tamil page was sent through the checklist | Upload a Tamil page if you want to try it |
| A dummy 12-digit number is masked in the panel | PENDING-USER | Needs the checklist panel | Demo and tests already mask `1234 5678 9012` | Look in the collapsed text section |
| Supabase row has metrics and masked text only | PENDING-USER | Do not create a row from this session | Code saves `quality_metrics` and `ocr_text_masked` after masking | Inspect `uploaded_documents` after one read |
| Status goes Uploaded, Processing, Processed | PENDING-USER | Needs the live checklist | The slot sets Processing, then the saved status | Watch one upload |
| Re-read document works | PENDING-USER | Needs a processed file | The button calls the process endpoint again | Click Re-read document |
| Replace resets, then reads again | PENDING-USER | Needs a live replace | Replace still sets `uploaded`, empty metrics, and null text, then the page starts a new read | Replace a file |
| A second user cannot process or read the file | PENDING-USER | Needs two accounts | Automated test returns 404 | Sign in as the other account and open the same URL |
| One document finishes in about 15 seconds | PENDING-USER | Depends on the photo | The demo images finished inside the test run | Time one clear page |
| Processed badge, not Passed | PENDING-USER | Needs the checklist | `slotStatus` returns Processed when there are no validation results | Confirm the teal Processed badge |
| Phone-sized screen | PENDING-USER | Needs the checklist on a phone | The home page rendered in a narrow browser. The new panel is a single-column stack | Open a checklist on a phone |

## Masking hardening

Follow-up after the OCR audit. Line breaks between digit groups now count as separators for 12-digit and 16-digit identifiers. Two identifiers separated only by whitespace stay separate, so they are not merged into one longer number. A 12-digit identifier still keeps the last four digits. A 16-digit VID still keeps the last four digits. Phone numbers, dates, six-digit PIN codes, and Tamil numerals stay unchanged. Masking a second time changes nothing.

| Check | Result | Evidence |
| --- | --- | --- |
| Focused masking tests | PASS | Plain, spaced, hyphenated, and newline-separated identifiers; adjacent identifiers; mixed labelled text; dates `17-11-2026` and `12/05/2003`; phone `9876543210`; PIN `600001`; Tamil numerals. A second mask pass returns the same text |
| Pytest counts | PASS | 45 passed, 0 skipped, 1 warning (`StarletteDeprecationWarning` from FastAPI's test client) |
| Frontend lint | PASS | `npm run lint` exited 0 |
| Frontend build | PASS | `npm run build` exited 0 on Next.js 16.4.6 |

## Verdict

AI work: PASS; live OCR tests: PENDING until the owner tests.

## Manual test steps for the owner

1. Start the backend and frontend with the commands below. If they are already running, leave them running.
2. Sign in and open a draft checklist.
3. Upload a clear English JPG or PNG. The slot should show "Reading your document…" and then the teal **Processed** badge, not Passed.
4. Open "Show text read from this document (ID numbers are hidden)" and confirm the words.
5. Upload a blurry photo of the same page. Its Sharpness number should be clearly lower.
6. Upload a dark photo. Its Brightness number should be low.
7. Upload a text PDF and confirm it reaches Processed.
8. Optional: upload a Tamil document and see whether the Tamil words appear.
9. Use a page that contains the dummy number `1234 5678 9012`. The text panel should show `XXXX XXXX 9012` and not the first two groups.
10. In Supabase, open `uploaded_documents` and confirm `quality_metrics` and `ocr_text_masked` are filled and the full number is absent.
11. Click **Re-read document** and wait for Processed again.
12. Replace the file. The old reading should clear, then a new read should start.
13. Sign in as a second user and confirm that user cannot process or open the first user's result.
14. Time one clear page. It should finish in about 15 seconds.
15. Repeat one checklist on a phone-width screen. Buttons stay tappable and the text panel scrolls.

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
.\.venv\Scripts\python.exe scripts\ocr_demo.py C:\path\to\document.jpg
```
