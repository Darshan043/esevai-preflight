# Step 4 verification report

**Project:** e-Sevai Pre-Flight – AI-Powered Government Document Readiness Assistant

**Date:** 16 November 2026

**Detected OS:** Windows, version 10.0.26200

## Gate results

| Gate | Result | Evidence |
| --- | --- | --- |
| G1. SQL files, Step 3 commits, clean tree | PASS | The eight required files exist. Log contains `279cdbb`, `dd2e2c8`, and `e22d372`. The tree was clean before the read-only check script. |
| G2. Env readiness | PASS | `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `NEXT_PUBLIC_SUPABASE_URL`, and `NEXT_PUBLIC_SUPABASE_ANON_KEY` are set. Both env files are ignored by Git. Values were not printed. |
| G3. Live database | PASS | `community-certificate` exists, required documents count is 5, at least one admin profile exists, bucket `documents` is private, and the other three tables responded. |
| G4. `verify_step3.sql` every row PASS | PASS | Owner answered yes. |

## Checks

| Check | Result | Evidence | Reason if not PASS | Fix |
| --- | --- | --- | --- | --- |
| Gate passed | PASS | G1–G4 passed before auth code was added. | | |
| Backend auth module | PASS | `backend/app/auth.py` and `backend/app/supabase_client.py` verify the bearer token and load the role from `profiles`. | | |
| `/me` and `/admin/ping` created | PASS | `GET /me` and `GET /admin/ping` are registered in `backend/app/main.py`. `/health` stays public. | | |
| pytest results | PASS | `10 passed` in `backend` (`tests/test_auth.py` 9, `tests/test_health.py` 1). | | |
| 401 checks | PASS | With the API on port 8000: `/health` 200, `/me` without a token 401, `/me` with an invalid token 401, `/admin/ping` without a token 401. | | |
| lint | PASS | `npm run lint` in `frontend` exited 0. | | |
| build | PASS | `npm run build` exited 0. Next.js 16.4.6 listed `/`, `/login`, `/signup`, `/dashboard`, `/admin`, and the proxy. | | |
| Protected routes redirect | PASS | Unauthenticated `GET /dashboard` returned 307 to `/login?next=%2Fdashboard`. `GET /admin` returned 307 to `/login?next=%2Fadmin`. `/`, `/login`, and `/signup` returned 200. | | |
| No secrets committed | PASS | Staged diff had no `eyJ`, `sk-ant`, or `service_role`. `.env`, `.env.local`, `.venv`, and `node_modules` were not staged. | | |
| Commit and push | PASS | `0f2aa2591557ad6e73a1db9bfeb059a0c167a188` — `Step 4: authentication – Supabase Auth, protected routes, backend JWT verification, admin role`. Push updated `e22d372..0f2aa25` on `origin/main`. | | |
| Working tree clean | PASS | After that push, `main` matched `origin/main`. This report is a separate commit. | | |
| Signup works with a new real email | PENDING-USER | Not attempted. Real credentials were not used. | The owner must sign up in the browser. | Open `/signup` and create an account. |
| Login works | PENDING-USER | Not attempted with a real account. | The owner must log in. | Open `/login` and sign in. |
| Logout works | PENDING-USER | Not attempted in the browser. | The owner must use Sign out. | Click Sign out and confirm the home page shows Login. |
| Citizen cannot open `/admin` | PENDING-USER | The server renders Access denied for a non-admin, but a real citizen session was not used. | The owner must try with a citizen account. | Log in as a citizen and open `/admin`. |
| Admin account can open `/admin` | PENDING-USER | The admin API check passed only with a test token, not a real admin session. | The owner must use the promoted admin account. | Log in as the admin and open `/admin`. |
| Dashboard backend card shows success | PENDING-USER | `/me` was checked without a real session. | The owner must view the card while signed in and while the API is running. | Open `/dashboard` and confirm Backend connection says Success. |
| New signup appears in profiles as citizen | PENDING-USER | The database trigger was not exercised with a new signup. | The owner must confirm the new row. | In Supabase, check `profiles.role` for the new user. |

## Overall verdict

AI work: PASS; live login tests: PENDING until the owner tests

## Manual test steps for the owner

1. Start the backend from `backend`:
   ```powershell
   .\.venv\Scripts\Activate.ps1
   uvicorn app.main:app --reload --port 8000
   ```
2. Start the frontend from `frontend`:
   ```powershell
   npm run dev
   ```
3. Open http://localhost:3000. Confirm Login and Sign up are shown, and the system-status card still loads.
4. Sign up with a new email address, a full name, and a password of at least 8 characters. If Supabase asks you to confirm the email, use the message in your inbox, then log in.
5. Confirm the dashboard says Welcome with your name, shows your email and the citizen role, and the Backend connection card says Success.
6. Open http://localhost:3000/admin while signed in as that citizen. Confirm the page says Access denied.
7. Sign out. Confirm the home page shows Login and Sign up again.
8. Log in as the admin account created in Step 3. Confirm `/admin` shows Admin area and the admin check message.
9. In the Supabase table editor, confirm the new signup has a `profiles` row with role `citizen`.
