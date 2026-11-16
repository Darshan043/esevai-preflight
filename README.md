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

The six required dummy sample files are in `sample-docs/` and are Git-ignored. The original Word files and the earlier misnamed images were kept. Step 1 checks passed on 16 November 2026.

## How to run

_Placeholder. Application setup will be added in a later step._
