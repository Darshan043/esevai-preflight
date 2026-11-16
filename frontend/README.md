# Frontend

Next.js app for e-Sevai Pre-Flight. The home page calls the backend health check.

## Run (Windows PowerShell)

From the repository root:

```powershell
cd frontend
npm install
npm run dev
```

Open http://localhost:3000

Copy `.env.example` to `.env.local` if that file is missing. `.env.local` is only for your machine and must not be committed.

## Build

```powershell
npm run lint
npm run build
```

## macOS / Linux

The commands are the same: `npm install`, `npm run dev`, `npm run lint`, and `npm run build`.
