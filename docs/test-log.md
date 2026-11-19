# Manual test log

Owner fills **Result** and **Notes**. Leave those columns empty until you run the test. Do not invent results.

Use a dedicated test account. Do not put passwords or keys in this file.

| ID | Area | Test | Expected result | Result (PASS/FAIL) | Notes |
| --- | --- | --- | --- | --- | --- |
| A1 | Auth | Sign up with a new email | Account is created; confirmation matches the project setting |  |  |
| A2 | Auth | Log in with a confirmed account | Dashboard (or `?next=` path) opens |  |  |
| A3 | Auth | Log out | Session ends; protected pages send the browser to login |  |  |
| A4 | Auth | Open `/dashboard` while signed out | Redirect to `/login?next=/dashboard` |  |  |
| A5 | Auth | Citizen opens `/admin` | Access denied; admin APIs reject the token |  |  |
| A6 | Auth | Admin opens `/admin` | Overview loads |  |  |
| U1 | Upload | Upload a JPG, a PNG, and a PDF into checklist slots | All three are accepted and listed |  |  |
| U2 | Upload | Upload a fake PDF (wrong bytes, `.pdf` name) | File is rejected; no storage object |  |  |
| U3 | Upload | Upload a file larger than the slot / `MAX_UPLOAD_MB` | File is rejected |  |  |
| U4 | Upload | Click Preview on a stored file | Image or PDF preview opens from a signed URL |  |  |
| U5 | Upload | Replace a stored file | New file is stored; old preview/OCR is cleared |  |  |
| U6 | Upload | Delete a stored file | Slot is empty; checklist no longer shows that file |  |  |
| O1 | OCR and AI | Process a clear document | OCR text and quality look usable |  |  |
| O2 | OCR and AI | Process a blurry photo | Quality check flags blur |  |  |
| O3 | OCR and AI | Process a dummy ID number | Masked form is shown (`XXXX` + last 4); full number is not stored |  |  |
| O4 | OCR and AI | Open the AI details panel | Extracted fields from masked text are shown |  |  |
| O5 | OCR and AI | Explain issues in English, then Tamil | Short explanations appear in each language |  |  |
| O6 | OCR and AI | Set `AI_ENABLED=false` (or wait for the off message) | Uploads and checks still work; AI routes say assistance is off |  |  |
| V1 | Validation and report | Good complete set | Report label is Ready |  |  |
| V2 | Validation and report | Mixed set (some warnings) | Report label is Almost ready |  |  |
| V3 | Validation and report | Bad or missing mandatory documents | Report label is Not ready |  |  |
| V4 | Validation and report | Replace a file after a report exists | Stale-report warning; application returns to draft |  |  |
| V5 | Validation and report | Print / Save as PDF | Print view is clean (no nav chrome) |  |  |
| M1 | Admin | Open `/admin` overview | Totals and charts load; users are hashed labels only |  |  |
| M2 | Admin | Create a new service and use it as a citizen | Citizen sees it with no code change |  |  |
| M3 | Admin | Save an invalid rule | Save is rejected with a field error |  |  |
| M4 | Admin | Change a slug or delete a used service | Locks apply (slug frozen; delete blocked if used) |  |  |
| P1 | Privacy and security | Second user opens the first user's application, preview, or report URL | All three are denied |  |  |
| P2 | Privacy and security | Inspect application / OCR / report rows in Supabase | No full ID numbers and no raw OCR text |  |  |
| P3 | Privacy and security | Preview a file; wait for the signed URL to expire | Bucket `documents` is private; expired URL fails |  |  |
| P4 | Privacy and security | Browser Network tab on login, upload, and AI | No service-role key and no Gemini/Anthropic key |  |  |
| L1 | Live deployment | Open `<APP_URL>` | Homepage loads over HTTPS |  |  |
| L2 | Live deployment | Open `<API_URL>/health` and `/health/ready` | `/health` is ok; ready shows `ocr=ok` and `tamil_ocr=yes` |  |  |
| L3 | Live deployment | Full citizen flow on the live site | Upload, OCR, checks, and report complete |  |  |
| L4 | Live deployment | Phone browser on the live site | Layout and upload work on a small screen |  |  |
| L5 | Live deployment | Admin on the live site | `/admin` works for the admin account only |  |  |
| F1 | Performance | Time to process one document | Local target under ~15 s; also note the live Render free-tier time |  |  |

## Bug log

| ID | Description | Severity | Fixed? | Commit |
| --- | --- | --- | --- | --- |
|  |  |  |  |  |
|  |  |  |  |  |
|  |  |  |  |  |

## Known limitations

Edit this list as you learn more from live use.

- Name and date extraction is a heuristic, backed by Gemini when a result is saved. The rule engine, not the model, decides pass or fail.
- Rate limits and the daily AI cap live in process memory. They reset when the backend restarts.
- A Render free instance sleeps after about 15 minutes idle. The first request after sleep can take 30–60 seconds.
- Admin statistics reflect the data that exists now. They are not a historical warehouse.
- Render free has 512 MB RAM. Large or high-DPI PDFs can run out of memory; lower `OCR_PDF_DPI` and `OCR_MAX_PDF_PAGES` if that happens.
