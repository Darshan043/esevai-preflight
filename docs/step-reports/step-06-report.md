# Step 6 verification report

Date: 17 November 2026

OS: Windows (win32 10.0.26200), PowerShell

## Gate results

GATE PASSED – Step 5 verified. No Step 5 fixes were required, so there is no "Step 5: fixes before Step 6" commit.

| Check | Result | Evidence |
| --- | --- | --- |
| B1. Step 5 files | PASS | Pages `/`, `/services`, `/services/[slug]`, `/applications`, `/applications/[id]`; `StatusBadge`; `Disclaimer`; `src/lib/types.ts`; `docs/step-reports/step-05-report.md`; `backend/app/auth.py`; `backend/app/supabase_client.py`; `backend/app/routers/me.py`. |
| B2. Step 5 commits | PASS | `git log --oneline -10` contains `9d5cb3d` "Step 5: frontend core UI..." and `7305173` "Step 5: verification report". |
| B3. Env readiness | PASS | Backend `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`: set. Frontend `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, and `NEXT_PUBLIC_API_URL`: set. Both env files are gitignored. Tracked files do not contain secret values. |
| B4. Database | PASS | Service `community-certificate` exists. Active required documents: 5. Bucket `documents` exists and is private. |
| B5. Manual Step 5 tests | PASS | The owner said Step 5 manual testing is complete and the listed flows work. |
| F1. Git sync | PASS | After `git fetch`, local `main` matched `origin/main` at `e463d31` and the tree was clean. |
| F2. pytest | PASS | 10 passed before Step 6 code. |
| F3. lint and build | PASS | `npm run lint` and `npm run build` exited 0. |
| F4. Page curls | PASS | `/` 200, `/services` 200, `/services/community-certificate` 200, `/applications` 307 to `/login?next=%2Fapplications`. Backend `/health` 200. |

## Step 6 checks

| Check | Result | Evidence | Reason if not PASS | Fix |
| --- | --- | --- | --- | --- |
| Gate passed | PASS | B1–B5 and F1–F4 passed. No Step 5 code was changed. | | |
| Storage helpers | PASS | `upload_object`, `delete_objects`, `create_signed_url`, and REST insert/update/delete helpers are in `backend/app/supabase_client.py`. Signed links accept `signedURL` and `signedUrl`. | | |
| Five endpoints | PASS | Upload, list, preview URL, delete document, and delete application are in `backend/app/routers/documents.py` and registered in `main.py`. `/health` stays public. | | |
| pytest count | PASS | `28 passed` in `backend` (1 Starlette httpx deprecation warning). | | |
| lint | PASS | `npm run lint` in `frontend` exited 0. | | |
| build | PASS | `npm run build` exited 0. Next.js 16.4.6. | | |
| POST upload without a token | PASS | 401 | | |
| GET preview-url without a token | PASS | 401 | | |
| DELETE document without a token | PASS | 401 | | |
| DELETE application without a token | PASS | 401 | | |
| GET /health | PASS | 200 | | |
| GET / logged out | PASS | 200 | | |
| GET /applications logged out | PASS | 307 to `/login?next=%2Fapplications` | | |
| Ownership on every endpoint | PASS | Each route loads the application or document with the caller's `user_id` and returns 404 otherwise. Admins have no bypass. | | |
| Service-role key stays on the backend | PASS | `frontend/src` has no service-role key, `eyJ`, or `sb_secret`. | | |
| Storage paths and signed URLs are not logged | PASS | The new backend modules do not print or log headers, paths, or signed URLs. The preview modal keeps a link only while it is open. | | |
| Filenames are sanitised | PASS | `sanitize_filename` strips directories, drops leading dots, and keeps letters, digits, dot, dash, and underscore. A `../../x.pdf` name cannot add `..` to the storage path. | | |
| Oversized files stop early | PASS | `read_upload` reads 64 KiB chunks and raises 413 as soon as the total passes the limit. The test with `MAX_UPLOAD_MB=0` does not call `upload_object`. | | |
| No secrets or sample-docs committed | PASS | The Step 6 commit does not include `.env`, `.env.local`, `.venv`, `node_modules`, or `sample-docs`. Staged source has no secret-looking strings. | | |
| Commit and push | PASS | `fed1070` "Step 6: file upload and storage – validated uploads, signed previews, replace and delete" is on `origin/main`. This report is the following commit. | | |
| Tree clean | PASS | After the implementation commit, `git status` was clean. | | |
| JPG uploads | PENDING-USER | Live Storage was not written during AI verification. | The owner runs the upload. | |
| PNG uploads | PENDING-USER | Same as JPG. | The owner runs the upload. | |
| PDF uploads | PENDING-USER | Same as JPG. | The owner runs the upload. | |
| Text file renamed to .pdf is rejected | PENDING-USER | Covered by a mocked 415 test only. | The owner tries a real fake PDF. | |
| .txt is rejected | PENDING-USER | Covered by a mocked 415 test only. | The owner tries a real .txt file. | |
| File over 5 MB is rejected with a friendly message | PENDING-USER | Covered by a mocked 413 test and the client size check. | The owner tries a real large file. | |
| Progress bar and Cancel work | PENDING-USER | The controls are in `UploadSlot`. | The owner watches a real upload. | |
| Preview shows the image and opens the PDF | PENDING-USER | Preview requests a fresh signed URL each click. | The owner opens both kinds of file. | |
| Replace swaps the file and the old object disappears | PENDING-USER | The mocked replace test deletes the old object. | The owner checks Storage. | |
| Delete removes the file and row | PENDING-USER | The mocked delete test removes the object and the row. | The owner checks Storage and the table. | |
| Progress counter updates | PENDING-USER | The counter uses local state after upload or delete. | The owner uploads and deletes without reloading. | |
| File appears in Storage under `{user_id}/{application_id}/` | PENDING-USER | The path builder uses that shape. | The owner checks the bucket. | |
| Row appears in `uploaded_documents` | PENDING-USER | Insert is mocked in tests. | The owner checks the table. | |
| A second user cannot preview or delete the first user's document | PENDING-USER | The mocked other-user case returns 404. | The owner tries with a second account. | |
| Deleting an application removes its files from Storage | PENDING-USER | The endpoint deletes storage objects before the row. My applications calls that endpoint. | The owner deletes an application and checks the bucket. | |
| Phone-sized screen (camera or gallery) | PENDING-USER | The file input accepts `.jpg,.jpeg,.png,.pdf` and `image/*` and does not force the camera. | The owner tries a phone. | |

## Verdict

AI work: PASS; live upload tests: PENDING until the owner tests.

## Manual test steps for the owner

1. Start the backend and the frontend with the commands below. Sign in as the first citizen.
2. Open Community Certificate, start a check, and upload a real JPG, a real PNG, and a real PDF into three different slots. Each should show Uploaded, the file name, the size, and the time. The counter should rise without a full reload.
3. During an upload, confirm the progress bar moves and that Cancel stops it.
4. Preview the JPG and PNG. An image should open. Close it and preview again. Preview the PDF. It should open in a new tab.
5. Replace one file and confirm the new name is shown. In Supabase Storage, the old object under that application should be gone and the new object should remain.
6. Delete one file. The slot should return to Pending, the counter should drop, the row should leave `uploaded_documents`, and the object should leave Storage.
7. Try a `.txt` file, a text file renamed to `.pdf`, and a file larger than 5 MB. Each should be rejected with a clear message and nothing new should appear in Storage.
8. Sign in as a second user and try to preview or delete the first user's document. Both should fail. Sign back in as the first user, delete the application from My applications, and confirm its folder is gone from the `documents` bucket.
9. On a phone-width screen, use Choose file and confirm the picker offers the camera or the gallery.

### Start both servers (Windows PowerShell)

```powershell
cd D:\esevai-preflight\backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000
```

```powershell
cd D:\esevai-preflight\frontend
npm run dev
```

Open `http://localhost:3000`.
