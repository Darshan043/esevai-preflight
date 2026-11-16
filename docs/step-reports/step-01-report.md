# Step 1 verification report

**Date:** 16 November 2026

**Detected OS:** Microsoft Windows NT 10.0.26200.0 (Win32), PowerShell 5.1.26100.9818

## Environment and repository checks

| Check | Required? | Result | Evidence | Reason if not PASS | Fix |
| --- | --- | --- | --- | --- | --- |
| git installed | Yes | PASS | `git version 2.53.0.windows.3` | | |
| git identity configured | Yes | PASS | `user.name=Darshan043`; `user.email` is set | | |
| Node >= 20 | Yes | PASS | `v24.16.0` | | |
| npm | Yes | PASS | `11.13.0` | | |
| Python >= 3.11 | Yes | PASS | `Python 3.12.10` via `python`. `python3` is the Microsoft Store stub and is not used. | | |
| pip | Yes | PASS | `pip 25.0.1` (Python 3.12) | | |
| Tesseract installed | Yes | FAIL | `tesseract` is not recognized. Not present in the usual install folders. | Command not found | `winget install --id UB-Mannheim.TesseractOCR -e --accept-package-agreements --accept-source-agreements` then open a new terminal. If still missing, add `C:\Program Files\Tesseract-OCR` to the user Path. |
| Tesseract has eng | Yes | FAIL | `tesseract --list-langs` could not run | Tesseract is not installed, so languages cannot be listed | Install Tesseract (English is included by the UB Mannheim installer), then run `tesseract --list-langs` and confirm `eng`. |
| Tesseract has tam | Yes | FAIL | `tesseract --list-langs` could not run | Tesseract is not installed, and Tamil data is not part of the default install | After Tesseract is installed, in an elevated PowerShell: `Invoke-WebRequest -Uri "https://github.com/tesseract-ocr/tessdata/raw/main/tam.traineddata" -OutFile "$env:ProgramFiles\Tesseract-OCR\tessdata\tam.traineddata"` then confirm `tam` in `tesseract --list-langs`. |
| Poppler | Yes | FAIL | `pdftoppm` is not recognized. Not present in the usual install folders. | Command not found | `winget install --id oschwartz10612.Poppler -e --accept-package-agreements --accept-source-agreements` then open a new terminal and run `pdftoppm -v`. If still missing, add that package's `Library\bin` folder to the user Path. |
| Docker (optional) | No | PASS | `Docker version 29.6.2, build dfc4efb` | | |
| .gitignore created | Yes | PASS | `.gitignore` present | | |
| README created | Yes | PASS | `README.md` present | | |
| folders created | Yes | PASS | `docs/`, `docs/step-reports/`, `sample-docs/`, `supabase/` (empty folders kept with `.gitkeep`) | | |
| docs templates created | Yes | PASS | `docs/SETUP_CHECKLIST.md`, `docs/service1-documents.md` | | |
| .env ignored | Yes | PASS | Temporary empty `.env` created. `git check-ignore -v .env` printed `.gitignore:2:.env	.env` (exit 0). File deleted afterward. | | |
| sample-docs ignored | Yes | PASS | Temporary `sample-docs/test.pdf` created. `git check-ignore -v sample-docs/test.pdf` printed `.gitignore:31:sample-docs/*	sample-docs/test.pdf` (exit 0). File deleted afterward. `sample-docs/.gitkeep` is not ignored. | | |
| git repo initialised | Yes | PASS | `git init -b main` in `D:\esevai-preflight`. Branch `main`. | | |
| remote origin set | Yes | PASS | `origin https://github.com/Darshan043/esevai-preflight.git` (fetch and push) | | |
| first commit made | Yes | PASS | `9f01613 Step 1: environment check, repo setup and project docs` | | |
| push to GitHub succeeded | Yes | PASS | `git push -u origin main` created `main` on origin. `git ls-remote origin` shows `9f016133ce4962a0407e20b74fcd82067611bf74` for `HEAD` and `refs/heads/main`. | | |
| working tree clean | Yes | PASS | After the first push: `nothing to commit, working tree clean`, branch up to date with `origin/main`. | | |

## Manual items (user-confirmed)

| Item | Answer | Status | Reminder |
| --- | --- | --- | --- |
| Supabase project created and URL, anon key, service-role key, JWT secret and DB password saved safely outside the repo | Yes | USER-CONFIRMED | |
| Anthropic API key created and credit added | No | PENDING | Create an Anthropic API key, add credit, and store it outside this repository. Do not commit the key. |
| Vercel account created and linked to GitHub | Yes | USER-CONFIRMED | |
| Render account created and linked to GitHub | Yes | USER-CONFIRMED | |
| Official Service 1 document list collected from the e-Sevai portal | No | PENDING | Collect the official Community Certificate document list from the Tamil Nadu e-Sevai portal and fill `docs/service1-documents.md`. Do not invent requirements. |
| 5–6 sample documents (dummy/redacted, including one blurry) collected | No | PENDING | Collect 5–6 dummy or redacted samples, including one blurry image, and keep them in `sample-docs/` locally. That folder's contents are gitignored except `.gitkeep`. |

## Overall verdict

**FAIL**

1. Tesseract is not installed. Install it with `winget install --id UB-Mannheim.TesseractOCR -e --accept-package-agreements --accept-source-agreements`, then open a new terminal. If `tesseract` is still missing, add `C:\Program Files\Tesseract-OCR` to the user Path.
2. Tesseract language `eng` could not be confirmed because Tesseract is not installed. After install, run `tesseract --list-langs` and confirm `eng`.
3. Tesseract language `tam` could not be confirmed because Tesseract is not installed. After install, from an elevated PowerShell run `Invoke-WebRequest -Uri "https://github.com/tesseract-ocr/tessdata/raw/main/tam.traineddata" -OutFile "$env:ProgramFiles\Tesseract-OCR\tessdata\tam.traineddata"`, then confirm `tam` in `tesseract --list-langs`.
4. Poppler (`pdftoppm`) is not installed. Install it with `winget install --id oschwartz10612.Poppler -e --accept-package-agreements --accept-source-agreements`, open a new terminal, and run `pdftoppm -v`. If the command is still missing, add that package's `Library\bin` folder to the user Path.
5. Anthropic API key is PENDING. Create the key, add credit, and save it outside the repo.
6. Official Service 1 document list is PENDING. Collect it from the e-Sevai portal and fill `docs/service1-documents.md`.
7. Sample documents are PENDING. Collect 5–6 dummy or redacted documents, including one blurry sample, and store them locally in `sample-docs/`.

## Next action

Not ready for Step 2. Before Step 2, install Tesseract (with `eng` and `tam`), install Poppler, create the Anthropic API key and add credit, collect the official Service 1 document list, and collect the sample documents.
