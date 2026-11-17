# Backend

FastAPI service for e-Sevai Pre-Flight. This step only exposes `GET /health`.

## Run (Windows PowerShell)

From the repository root:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## Run (macOS / Linux)

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

Health check: http://localhost:8000/health

Copy `.env.example` to `.env` only on your machine if you need to override the defaults. Do not commit `.env`.

## Tests

With the virtual environment activated, from the `backend` folder:

```powershell
pytest
```

## Read one local file

This does not use the database. It prints quality numbers and the masked text only.

```powershell
python scripts/ocr_demo.py C:\path\to\document.jpg
```

JPG, PNG, and PDF files are accepted. Set `TESSERACT_CMD` or `POPPLER_PATH` in `.env` when those tools are not on the system PATH.
