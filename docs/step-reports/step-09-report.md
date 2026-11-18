# Step 9 report – Gemini field extraction and simple explanations

Date: 18 November 2026

Implementation commit: `70c4580`
Message: Step 9: AI integration – Gemini field extraction and simple explanations

Report commit: `37cf07d`
Follow-up (uncommitted at this writing): sanitized provider-error handling, extraction JSON parsing, `GEMINI_MODEL=gemini-3.5-flash-lite`, and the two-column application workspace.

The production output cap stayed 800 tokens. The smoke test uses 1024 tokens so a short `OK` can be returned. An empty HTTP 200 is `empty_response`, not `network`. The API provider, SDK, API key, and token limits were not changed. The model name comes only from `GEMINI_MODEL`.

## Model timeline

| Event | Result | Evidence |
| --- | --- | --- |
| Owner extract/explain on `gemini-3.8-flash` | Provider failures | HTTP **429** `RESOURCE_EXHAUSTED`, then HTTP **503** and **504**, classified `network`. Retry ran once on transient 503/504. |
| Switch to `gemini-3.5-flash-lite` | PASS | SDK `models.get` returned **HTTP 200**, name `models/gemini-3.5-flash-lite`. Only `GEMINI_MODEL` in `backend/.env` was changed. |
| Live smoke test on lite | PASS | `scripts/ai_smoke_test.py` printed `model gemini-3.5-flash-lite` and `success`. Wall clock **5070 ms**. One run, no retry. |
| First owner extract on lite | Parse failure | Gemini answered. `parse_extraction` raised HTTP **502** `category=parse` (`extra="forbid"` rejected extra top-level keys). Masked OCR was present; `extracted_fields` stayed empty. |
| Parser change | PASS (automated) | Unknown top-level keys are dropped. Known fields stay strict. Invalid dates, confidence, last-4, and missing `extraction_confidence` still fail. |
| Owner Address Proof extract after parser fix | PASS | Document type Address Proof. Name **Arun Kumar**. Issue date **2026-11-01**. Last four digits **0001**. Confidence **high**. |

Earlier recorded live demos on `gemini-3.8-flash` (smoke success; synthetic extraction 5.3 s, 253/75 tokens; English explanation 6.3 s, 168/65; Tamil explanation 9.0 s, 168/74) remain valid. They are not the later owner Address Proof retries.

## Automated tests

| Check | Result | Evidence |
| --- | --- | --- |
| Pre-flight gates B1–B8 | PASS | Reports and commits through `b66ae1d`, then Step 9 implementation `70c4580`. |
| Focused smoke tests | PASS | Empty HTTP 200 is `empty_response`. One retry on HTTP 503. Short 429 is rate limited. Confirmed daily quota is not retried. Bare `RESOURCE_EXHAUSTED` stays quota. |
| AI modules and routes | PASS | Extraction, explanations, limits, client, hygiene, and `/extract`, `/explain`, `/ai-advice`. |
| Backend pytest | PASS | **87 passed**. No test constructed a real Gemini client (`tests/conftest.py` autouse guard). |
| Frontend tests | PASS | **10 passed** (`tests/ai.test.ts` 5, `tests/replacement.test.ts` 5). |
| Frontend lint | PASS | `npm run lint` exit 0. |
| Frontend production build | PASS | `npm run build` exit 0 on Next.js 16.4.6. |
| Unauthenticated routes | PASS | Extract 401, explain 401, ai-advice 401, health 200. |
| Privacy and injection | PASS | Prompts keep document text in a data tag. Logs record ids, model, duration, tokens, category, HTTP status, and a sanitized parse `rule`. They do not record keys, OCR, prompts, or model replies. |
| AI disabled (automated) | PASS | `AI_ENABLED=false` returns HTTP 503 with `AI assistance is turned off.` |
| Provider-error handling (automated) | PASS | Network 503 retries once. Explain returns HTTP 429 for a temporary rate limit and HTTP 503 for confirmed quota. The application daily limit stays a separate 429 sentence. |
| Deterministic validation without AI | PASS | `tests/test_validation.py` 13 passed. Validation does not call Gemini. |

## Owner tests that passed

| Check | Result | Evidence |
| --- | --- | --- |
| `AI_ENABLED=false` | PASS | Test 9: health 200, owner auth still worked, OCR processed a fictional Address Proof, rule-based validation wrote checklist rows, extract and explain returned HTTP 503 `AI assistance is turned off.`, and no Gemini request log appeared. |
| Standard checks while AI fails | PASS | Process and validate returned 200 while extract returned 503 or 502. Checklist rows were still stored. |
| Replace then delete clears AI data | PASS | Replacement stayed on the same Address Proof slot. Deletion cleared extracted fields and saved advice for that document and left Self-Declaration unchanged. |
| Second user blocked | PASS | A different signed-in account could not open the owner application. |
| Retry policy on live 503/504 | PASS | Two Gemini attempts (`attempt=1` and `attempt=2`) then HTTP 503. The one-retry policy ran. |
| Owner Address Proof extraction after parser fix | PASS | Address Proof: Arun Kumar; issue date 2026-11-01; last four 0001; confidence high. |

## Owner tests that remain unverified

Synthetic English and Tamil explanations already succeeded. The owner application did not get a successful live explain.

| Check | Result | Evidence |
| --- | --- | --- |
| Owner English “Explain issues in simple words” | UNVERIFIED | Earlier owner explain returned HTTP 503 (quota, then unavailability). No later owner confirmation of a successful English explain. |
| Owner Tamil explanation | UNVERIFIED | Synthetic Tamil demo passed. The owner application was not successfully explained in Tamil. |
| Re-run hides stale owner advice | UNVERIFIED | Covered by automated tests. Not confirmed after a successful owner explain. |
| Two-column workspace in the browser | UNVERIFIED | Implemented in code. Browser verification is still pending. |
| Phone width | UNVERIFIED | Not opened at a narrow viewport. |
| Gemini Console usage after owner tests | UNVERIFIED | Not inspected in the Google console. |

## Two-column application workspace

Added after Step 9 AI work. Layout only. Validation state and API calls are unchanged.

- Left: the five document cards, with upload, replace, delete, re-read, quality, OCR text, and AI-extracted details.
- Right: sticky readiness panel with the full checklist, passed and failed checks, Re-run checks, Explain issues in simple words, and AI advice.
- Below the `lg` breakpoint: one column, results panel first, then the document cards.
- Browser verification is still pending.

## External dependency

AI provider availability is outside this repository. Deterministic OCR and rule-based validation continue when Gemini is off, rate-limited, over quota, or returning HTTP 503/504.

## Closure checks

| Check | Result | Evidence | Reason if not PASS | Fix |
| --- | --- | --- | --- | --- |
| Backend pytest | PASS | 87 passed |  |  |
| Frontend tests | PASS | 10 passed |  |  |
| Frontend lint and build | PASS | lint 0, build 0 |  |  |
| Live smoke on `gemini-3.5-flash-lite` | PASS | success, 5070 ms |  |  |
| Owner Address Proof extract after parser fix | PASS | Fields listed above |  |  |
| Owner English/Tamil explain | UNVERIFIED | No successful owner explain | Live explain not repeated after the model switch | Try explain once when the API is healthy. Do not change the model. |
| Two-column workspace | UNVERIFIED | Code only | Browser check not done | Open the application page on desktop and a narrow viewport. |
| No secrets in the tree to commit | PASS | `.env` is gitignored. Reports do not contain keys. |  |  |
| Implementation pushed | PARTIAL | `70c4580` and `37cf07d` are on `origin/main`. Follow-up parsing, lite model docs, and the workspace UI are not committed. |  |  |

Verdict: Step 9 AI integration is complete for extraction, with `gemini-3.5-flash-lite` after 3.8 Flash 503/504/429 failures. Automated tests pass. Owner Address Proof extraction passed after the parser fix. Owner English and Tamil explanations remain unverified. The two-column workspace is implemented and not yet browser-verified.

## Manual test

Restart both servers so they load this step.

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
14. Confirm the two-column workspace on a wide screen: documents on the left, readiness panel sticky on the right.
15. Do not start Step 10.

Item 3 passed on Address Proof after the parser fix. Items 8–9 (replace/delete), 11, and 12 (`AI_ENABLED=false`) passed. Items 6–7 and 13–14 remain unverified.
