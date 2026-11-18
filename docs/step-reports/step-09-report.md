# Step 9 report – Gemini field extraction and simple explanations

Date: 18 November 2026

Implementation commit: `70c4580`  
Message: Step 9: AI integration – Gemini field extraction and simple explanations

The model name stayed `gemini-3.8-flash`. The production output cap stayed 800 tokens. The smoke test uses 1024 tokens so a short `OK` can be returned. An empty HTTP 200 is `empty_response`, not `network`.

| Check | Result | Evidence | Reason if not PASS | Fix |
| --- | --- | --- | --- | --- |
| Pre-flight gates B1–B8 | PASS | Reports, commits through `b66ae1d`, env names, OCR tools, database, and the owner's Step 8 confirmation were already recorded. `HEAD` matched `origin/main` before this work. |  |  |
| Live smoke test | PASS | `scripts/ai_smoke_test.py` printed `model gemini-3.8-flash` and `success`. |  |  |
| Focused smoke tests | PASS | 10 passed, including empty HTTP 200 as `empty_response`. |  |  |
| AI modules and routes | PASS | Extraction, explanations, limits, client, hygiene, and `/extract`, `/explain`, `/ai-advice` are in the backend. |  |  |
| Backend pytest | PASS | 80 passed. No test called Google. A guard refuses a real Gemini client. |  |  |
| Prompt preview | PASS | `scripts/ai_prompt_preview.py` printed prompts built from the name EXAMPLE PERSON and one synthetic warning. |  |  |
| Synthetic live demo | PASS | Extraction 5.3 s, 253/75 tokens. English explanation 6.3 s, 168/65 tokens. Tamil explanation 9.0 s, 168/74 tokens. |  |  |
| Frontend lint and build | PASS | `npm run lint` and `npm run build` exited 0 on Next.js 16.4.6. Frontend AI helper tests: 3 passed. |  |  |
| Unauthenticated routes | PASS | On a temporary server at port 8010: extract 401, explain 401, ai-advice 401, health 200. Existing frontend: `/` 200, `/applications` 307 to login. |  |  |
| Privacy and injection | PASS | Prompts keep document text in a data tag. Parsers reject unknown fields, bad last-4 values, and unknown explanation ids. Logs record ids, model, duration, tokens, and status. |  |  |
| No secrets in the commit | PASS | The only secret-like scan hit was an integrity hash in `frontend/package-lock.json`, which was not part of this change. `.env` was not staged. |  |  |
| Implementation pushed | PASS | `b66ae1d..70c4580` on `origin/main`. |  |  |
| AI details panel in the browser | PENDING-USER | Needs a signed-in checklist. |  | Open an application after both servers restart. |
| AI name used for a mismatch | PENDING-USER | Covered by automated tests only. |  | Upload two documents whose AI names differ. |
| Expired document from an AI expiry date | PENDING-USER | Covered by automated tests only. |  | Use a document with a past expiry. |
| English explanation | PENDING-USER | Synthetic demo only. |  | Press “Explain issues in simple words” with English selected. |
| Tamil explanation | PENDING-USER | Synthetic demo returned Tamil. |  | Switch to தமிழ் and explain again. |
| AI unavailable while checks still run | PENDING-USER | Automated 502 path only. |  | Stop the model or the network and read a document. |
| `AI_ENABLED=false` | PENDING-USER | Automated 503 only. |  | Set the flag, restart the API, and read a document. |
| Re-run hides stale advice | PENDING-USER | Logic is in the checklist. |  | Explain, then re-run checks. |
| Replace or delete clears AI details | PENDING-USER | Server clears saved fields and advice. |  | Replace a file and delete a file. |
| Saved fields have no raw OCR or full ID | PENDING-USER | Parser keeps last 4 only. |  | Inspect `extracted_fields` and `summary.ai_advice` in Supabase. |
| Second user blocked | PENDING-USER | Automated 404 only. |  | Sign in as another user and open the same ids. |
| Gemini Console usage stays small | PENDING-USER | This session used the smoke call plus three synthetic calls. |  | Check the console after the manual tests. |
| Phone width | PENDING-USER | Not opened in a browser. |  | Narrow the checklist and use the AI controls. |

Verdict: AI work: PASS; live AI tests: PENDING until the owner tests.

## Manual test

Restart both servers so they load this step. The copies that were already running do not include it.

```powershell
cd D:\esevai-preflight\backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

```powershell
cd D:\esevai-preflight\frontend
npm run dev
```

1. Sign in and open a draft application.
2. Upload a clear document. Confirm “AI is reading the details…”, then the checklist checks.
3. Open “Details read by AI” and confirm the mistake warning. The badge still comes from the checks.
4. Use a document whose saved name differs from another document and confirm the name check follows that difference.
5. Use a document with an expiry date in the past and confirm it needs a fix.
6. With English selected, press “Explain issues in simple words”. Read the lines and the overall tip.
7. Switch to தமிழ் and explain again.
8. Re-run checks and confirm the previous explanation disappears.
9. Replace the file, then delete a file, and confirm the AI details and the explanation are gone.
10. In Supabase, confirm `extracted_fields` and `summary.ai_advice` do not contain a full ID number or the raw OCR page.
11. Sign in as a second user and confirm those document and application ids return not found.
12. Set `AI_ENABLED=false`, restart the API, read a document, and confirm the checks still run.
13. Repeat the checklist at a narrow phone width.
14. Do not start Step 10.
