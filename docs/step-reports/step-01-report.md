# Step 1 verification report

**Project:** e-Sevai Pre-Flight – AI-Powered Government Document Readiness Assistant

**Date:** 16 November 2026

**Detected OS:** Microsoft Windows NT 10.0.26200.0 (Win32), PowerShell 5.1.26100.9818

Planned AI provider: Google Gemini API.

Commands below were run in this session. Tesseract and Poppler were missing from the inherited shell Path. They were found on the saved Machine and User Path, and the commands succeeded after that Path was loaded.

## Technical verification

| Check | Required? | Result | Evidence | Reason if not PASS | Fix |
| --- | --- | --- | --- | --- | --- |
| git installed | Yes | PASS | `git version 2.53.0.windows.3` | | |
| git identity configured | Yes | PASS | `user.name=Darshan043`; `user.email` is set | | |
| Node >= 20 | Yes | PASS | `v24.16.0` | | |
| npm | Yes | PASS | `11.13.0` | | |
| Python >= 3.11 | Yes | PASS | `Python 3.12.10` via `python` | | |
| pip | Yes | PASS | `pip 25.0.1 from C:\Users\lenovo\AppData\Local\Programs\Python\Python312\Lib\site-packages\pip (python 3.12)` | | |
| Tesseract installed | Yes | PASS | `tesseract v5.4.0.20240606` from `C:\Program Files\Tesseract-OCR\tesseract.exe`. `winget list` shows `UB-Mannheim.TesseractOCR 5.4.0.20240606`. | | |
| Tesseract has eng | Yes | PASS | `tesseract --list-langs` lists `eng`, `osd`, and `tam`. `eng.traineddata` is in the tessdata folder. | | |
| Tesseract has tam | Yes | PASS | `tam` is in `tesseract --list-langs`. `tam.traineddata` is in the tessdata folder. | | |
| Poppler | Yes | PASS | `pdftoppm version 25.07.0`. `winget list` shows `oschwartz10612.Poppler 25.07.0-0`. Binary directory: `C:\Users\lenovo\AppData\Local\Microsoft\WinGet\Packages\oschwartz10612.Poppler_Microsoft.Winget.Source_8wekyb3d8bbwe\poppler-25.07.0\Library\bin` | | |
| Docker (optional) | No | PASS | `Docker version 29.6.2, build dfc4efb` | | |

## Repository verification

| Check | Required? | Result | Evidence | Reason if not PASS | Fix |
| --- | --- | --- | --- | --- | --- |
| .gitignore present | Yes | PASS | `.gitignore` inspected | | |
| README present | Yes | PASS | `README.md` inspected. Planned AI provider updated to Google Gemini API. | | |
| docs folder present | Yes | PASS | `docs/`, `docs/SETUP_CHECKLIST.md`, `docs/service1-documents.md` | | |
| step-reports folder present | Yes | PASS | `docs/step-reports/step-01-report.md` and `docs/step-reports/.gitkeep` | | |
| sample-docs folder present | Yes | PASS | `sample-docs/` exists | | |
| supabase folder present | Yes | PASS | `supabase/.gitkeep` | | |
| .env ignored | Yes | PASS | Temporary empty `.env` created. `git check-ignore -v .env` printed `.gitignore:2:.env	.env` (exit 0). File deleted. `.env` is not present afterward. | | |
| sample documents ignored | Yes | PASS | `git check-ignore -v sample-docs/test.pdf` printed `.gitignore:31:sample-docs/*	sample-docs/test.pdf` (exit 0). No sample file was created for this check. | | |
| sample-docs/.gitkeep tracked | Yes | PASS | `git check-ignore -q sample-docs/.gitkeep` exited 1 (not ignored). `git ls-files` includes `sample-docs/.gitkeep`. | | |
| five or six sample documents exist | Yes | FAIL | `Get-ChildItem -Force sample-docs` shows only `.gitkeep` (length 0). A full file listing of the project root shows no image or PDF sample files. | No dummy documents are in the repository | Add 5–6 dummy or redacted files to `sample-docs/` locally. The ignore rule will keep them out of Git. |
| at least one blurry sample | Yes | FAIL | No sample files exist to inspect | Cannot check blur without files | Include one deliberately blurry dummy image among the local samples. |
| no secrets or real personal documents committed | Yes | PASS | `git ls-files` lists only `.gitignore`, `README.md`, `docs/SETUP_CHECKLIST.md`, `docs/service1-documents.md`, `docs/step-reports/.gitkeep`, `docs/step-reports/step-01-report.md`, `sample-docs/.gitkeep`, and `supabase/.gitkeep`. No `.env`, key, or sample document is tracked. Secret values were not requested or read. | | |
| git repo and origin | Yes | PASS | Branch `main`. Origin `https://github.com/Darshan043/esevai-preflight.git`. Earlier commits `9f01613` and `d19f803` are on origin. | | |

## Manual items (user-confirmed)

| Item | Status | Evidence |
| --- | --- | --- |
| Supabase project created, and project URL, anon key, service-role key, JWT secret, and DB password saved safely outside the repo | USER-CONFIRMED | Stated by the project owner. Values were not inspected and are not in Git. |
| Google Gemini API key created | USER-CONFIRMED | Stated by the project owner. The key was not requested, displayed, or stored. Planned provider is Google Gemini API, replacing Anthropic Claude API. |
| Vercel account created and linked to GitHub | USER-CONFIRMED | Stated by the project owner. Account linkage was not inspected from Vercel. |
| Render account created and linked to GitHub | USER-CONFIRMED | Stated by the project owner. Account linkage was not inspected from Render. |
| Official Community Certificate document list collected | USER-CONFIRMED | FAQ Question 7 and the live Service List were fetched on 16 November 2026. The DNC discrepancy is recorded below and in `docs/service1-documents.md`. It is not treated as resolved. |
| 5–6 dummy/redacted sample documents, including one blurry document | NOT CONFIRMED | The project owner reported this as done. The `sample-docs/` directory contains only `.gitkeep`. No document file was found to inspect, so this is not marked USER-CONFIRMED. |

## Official Community Certificate document requirements

Department: Revenue Administration. Service: Community Certificate. Service code: REV-101, from the FAQ instruction to open "REV-101 Community Certificate".

Sources checked on 16 November 2026:

- FAQ Question 7: https://www.tnesevai.tn.gov.in/citizen/Pages/FAQ.aspx#collapseSeven
- Service List URL supplied for this project: https://www.tnesevai.tn.gov.in/citizen/ServiceList.aspx — this URL returned HTTP 404
- Live Service List row that was actually read: https://www.tnesevai.tn.gov.in/citizen/Pages/ServiceList.aspx

The FAQ lists Photo, Address Proof, Community Certificate of Father or Mother or Siblings, and Self-Declaration of Applicant. The live Service List lists those items (with the wording "Any Address Proof") and additionally lists DNC Certificate. Accepted formats, Mandatory/Optional labels, expiry rules, and key fields are not specified in either source. Full rows are in `docs/service1-documents.md`.

## Overall verdict

**FAIL**

1. `sample-docs/` does not contain 5–6 dummy or redacted sample documents. Only `sample-docs/.gitkeep` is present.
2. A blurry sample cannot be confirmed because no sample document exists.

Tesseract (`eng` and `tam`), Poppler, Git, Node, Python, and the repository ignore rules passed. The official document list was checked, including the unresolved DNC difference. Gemini, Supabase, Vercel, and Render remain user-confirmed, without any secret values stored in the repo.

## Next action

Not ready for Step 2. Add 5–6 dummy or redacted sample documents, including one blurry document, to `sample-docs/` on this machine. Do not commit those files. After they are present, recheck the folder before starting Step 2.
