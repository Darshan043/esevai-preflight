# Setup checklist

Accounts and secret **names** only. Do not put secret values in this repository.

Planned AI provider: Google Gemini API.

- [x] GitHub repository — verified: `https://github.com/Darshan043/esevai-preflight.git`
- [x] Supabase project — USER-CONFIRMED. Secret values are stored outside this repo and were not inspected.
  - [x] Project URL
  - [x] Anon key
  - [x] Service-role key
  - [x] JWT secret
  - [x] Database password
- [x] Google Gemini API key — USER-CONFIRMED. The key is not stored in this repo.
- [x] Vercel account — USER-CONFIRMED, linked to GitHub
- [x] Render account — USER-CONFIRMED, linked to GitHub

Store every secret outside the repo (a password manager or a local file that Git ignores). Never commit `.env` files, keys, or passwords.

## Build progress

- [x] Step 1 – environment check, repository setup, and first Git push
- [x] Step 2 – scaffold: FastAPI backend, Next.js frontend, and health check
- [x] Step 3 – database SQL files created (schema, RLS, storage, and seed) and run in Supabase
- [x] Step 4 – authentication: signup, login, protected pages, backend JWT check, admin role
- [x] Step 5 – frontend core UI: landing, services, checklist, and my applications
- [x] Step 6 – file upload and storage: validated uploads, signed previews, replace and delete
- [x] Step 7 – image processing and OCR: quality metrics, Tesseract eng+tam, ID masking
- [x] Step 8 – document validation engine: config-driven checks, cross-document checks, results UI
- [x] Step 9 – Gemini field extraction and plain-language explanations. Configured model: `gemini-3.5-flash-lite`. `GEMINI_API_KEY` and `GEMINI_MODEL` must also be set in Render at deployment (Step 14).
- [x] Step 10 – readiness report: deterministic score and label, next steps, printable report page, score badge on My applications
- [x] Step 11 – admin dashboard: service and checklist management, aggregate statistics
- [x] Step 12 – integration and error handling: consistent errors, safe logging, production checks, rate limits, retention, frontend resilience
- [x] Step 13 – Docker: backend image with Tesseract eng+tam and Poppler, frontend production image, Compose for local Linux containers
- [ ] Step 14 – live deploy on Render (backend Docker) and Vercel (frontend). Owner follows `docs/deployment-guide.md`
- [ ] Two-column application workspace – implemented (documents left, sticky readiness panel right; single column below `lg`). Browser verification still pending.
