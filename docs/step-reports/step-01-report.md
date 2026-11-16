# Step 1 verification report

**Project:** e-Sevai Pre-Flight – AI-Powered Government Document Readiness Assistant

**Date:** 16 November 2026

**Detected OS:** Microsoft Windows 11 Home Single Language, version 10.0.26200

Planned AI provider: Google Gemini API.

Environment commands were run again after the sample correction. Sample files were opened and checked in this same pass. Government pages were not fetched again. The service text below is the text stored in `docs/service1-documents.md`.

## Environment verification

| Check | Result | Evidence |
| --- | --- | --- |
| Windows 11 | PASS | `Microsoft Windows 11 Home Single Language 10.0.26200` |
| Git | PASS | `git version 2.53.0.windows.3` |
| Node.js >= 20 | PASS | `v24.16.0` |
| npm | PASS | `11.13.0` |
| Python >= 3.11 | PASS | `Python 3.12.10` |
| pip | PASS | `pip 25.0.1` |
| Docker | PASS | `Docker version 29.6.2, build dfc4efb` |
| Tesseract | PASS | `tesseract v5.4.0.20240606` |
| Tesseract eng | PASS | `tesseract --list-langs` lists `eng` |
| Tesseract tam | PASS | `tesseract --list-langs` lists `tam` |
| Poppler | PASS | `pdftoppm version 25.07.0` |

## Sample document verification

Original files were left in place. New files use the required names.

Word is installed, but its window title was `Unlicensed Product` and `ExportAsFixedFormat` did not finish. The four PDFs were therefore built from the text inside the DOCX files. They are genuine PDF 1.4 files, not renamed Word files. The en dash in the Word text is a hyphen in the PDF because the embedded Helvetica encoding used a hyphen. The words `SAMPLE - NOT VALID` are visible.

| Expected file | Result | Evidence |
| --- | --- | --- |
| `01-dummy-photo.jpg` | PASS | New JPEG, 33,354 bytes, 640×800. Header is JPEG. It is a drawn fictional portrait, not a photograph of a person. The banner reads `SAMPLE – NOT VALID`. Tesseract read that banner, `FICTIONAL PORTRAIT`, and `Not a real person or document`. The image is sharp. The older `01-dummy-photo.jpg.jpeg` was not changed. |
| `02-dummy-address-proof.pdf` | PASS | 1,133 bytes. Header `%PDF-1.4`. `pdfinfo` reports 1 page, 612×792. `pdftotext` and a Poppler render show fictional address text for Arun Kumar, 12 Sample Street, Example Nagar, `SAMPLE-ADDR-0001`, and `SAMPLE - NOT VALID`. The DOCX remains. |
| `03-dummy-community-certificate.pdf` | PASS | 1,433 bytes. Header `%PDF-1.4`. `pdfinfo` reports 1 page. Text includes Sample Community A, Example District, `MOCK-COMM-0001`, and `SAMPLE - NOT VALID`. The DOCX remains. |
| `04-dummy-self-declaration.pdf` | PASS | 1,813 bytes. Header `%PDF-1.4`. `pdfinfo` reports 1 page. Text includes `MOCK-DECL-0001` and a statement that the declaration is fictional. The DOCX remains. |
| `05-dummy-dnc-certificate.pdf` | PASS | 1,905 bytes. Header `%PDF-1.4`. `pdfinfo` reports 1 page. Text includes Fictional DNC Category A, `MOCK-DNC-0001`, and `SAMPLE - NOT VALID`. The DOCX remains. |
| `06-blurry-photo.jpg` | PASS | New JPEG, 58,223 bytes, 1600×1100. Header is JPEG. Gaussian blur radius 3.2. The page is visibly soft, and Tesseract still read `SAMPLE – NOT VALID`, Arun Kumar, 12 Sample Street, Example Nagar, 05-11-2026, and `MOCK-TEST-0001`. The older `06-blurry-photo.jpg.png` was not changed. |

## Git and security

| Check | Result | Evidence |
| --- | --- | --- |
| Repository and branch | PASS | Branch `main`. Origin `https://github.com/Darshan043/esevai-preflight.git`. |
| Sample files ignored | PASS | `git check-ignore -v` matches `.gitignore:31:sample-docs/*` for all six required files. `git status --short` does not list them. |
| sample-docs/.gitkeep tracked | PASS | `git check-ignore -q sample-docs/.gitkeep` exits 1. `git ls-files` includes it. |
| .env ignored | PASS | `.gitignore` ignores `.env`. No `.env` file is present. |
| No sample or secret committed | PASS | The only tracked sample path is `sample-docs/.gitkeep`. Documentation contains no key, password, or token. |

## Documentation verification

| Check | Result | Evidence |
| --- | --- | --- |
| Purpose and folder structure | PASS | `README.md` |
| Google Gemini API, not Anthropic | PASS | `README.md` and `docs/SETUP_CHECKLIST.md` |
| Secret handling without secret values | PASS | Checklist and `.gitignore` |
| Supabase, Vercel, Render | PASS | Names only, marked user-confirmed |
| REV-101 Community Certificate | PASS | `docs/service1-documents.md` |
| FAQ four items | PASS | Photo, Address Proof, parent or sibling community certificate, self-declaration |
| Service List DNC item | PASS | Listed separately and not treated as resolved |
| Unknown fields | PASS | Formats, validity, and mandatory/optional status say `Not specified in official source – verify` |
| README sample status | PASS | Updated to say the six required files are present and Git-ignored |

## Manual items

| Item | Status |
| --- | --- |
| Supabase project and keys saved outside the repo | USER-CONFIRMED |
| Google Gemini API key created | USER-CONFIRMED. The key was not requested or displayed. |
| Vercel linked to GitHub | USER-CONFIRMED |
| Render linked to GitHub | USER-CONFIRMED |
| Official document list collected, with the DNC discrepancy recorded | USER-CONFIRMED |
| Six required dummy files, including one blurred image | TECHNICALLY VERIFIED from the files above |

## Overall verdict

**PASS – STEP 1 COMPLETE**

## Next action

Ready for Step 2 after this report is committed, if the project owner approves that commit. Do not commit anything in `sample-docs/` except `.gitkeep`.
