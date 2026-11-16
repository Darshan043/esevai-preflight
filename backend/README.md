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
