# e-Sevai Pre-Flight – AI-Powered Government Document Readiness Assistant

Checks whether a citizen's documents are complete and readable before they are submitted through Tamil Nadu e-Sevai.

## Planned tech stack

- Frontend: Next.js, TypeScript, Tailwind CSS (deployed on Vercel)
- Backend: Python FastAPI (deployed on Render with Docker)
- Data: Supabase (Postgres, Auth, Storage)
- AI: Google Gemini API
- Document processing: Tesseract OCR (English and Tamil), OpenCV, pdf2image (Poppler)

## Planned folder structure

```
/frontend     Next.js application
/backend      FastAPI application
/docs         Setup notes, service templates, step reports
/supabase     Database and storage configuration
```

## Status

Step 4 complete – authentication

## Authentication

A citizen signs up or logs in through Supabase Auth in the browser. The anon key stays in the frontend. The service-role key stays in `backend/.env` and is never sent to the browser.

Next.js `src/proxy.ts` refreshes the session and sends visitors who are not signed in from `/dashboard` and `/admin` to `/login`. Signed-in visitors are sent from `/login` and `/signup` to `/dashboard`. The server checks the user with `getUser()`.

The FastAPI backend checks the access token on `GET /me` and `GET /admin/ping`. It accepts HS256 tokens signed with `SUPABASE_JWT_SECRET` and ES256/RS256 tokens checked against the project JWKS. If those checks cannot be completed, it asks Supabase Auth to accept or reject the token. The role comes from the `profiles` table, not from the browser. New accounts are `citizen`. An admin is created only by `supabase/scripts/promote_admin.sql`. Admins can open `/admin`. Citizens see an access-denied page.

Frontend env names: `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`.
Backend env names: `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWT_SECRET`.

## Database

The schema, security rules, storage bucket, and Community Certificate seed are SQL files. Run them yourself in the Supabase SQL Editor. The order and expected result of each script are in [docs/step-03-run-order.md](docs/step-03-run-order.md). The table layout is explained in [docs/database-design.md](docs/database-design.md).

## How to run

The sample documents from Step 1 stay in `sample-docs/` and are Git-ignored.

### Backend (Windows PowerShell)

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Run the tests from `backend` with the virtual environment activated:

```powershell
pytest
```

### Backend (macOS / Linux)

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
pytest
```

### Frontend (Windows, macOS, and Linux)

```powershell
cd frontend
npm install
npm run dev
```

Open http://localhost:3000 while the backend is running on port 8000.
