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

Step 2 complete – scaffold running

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
