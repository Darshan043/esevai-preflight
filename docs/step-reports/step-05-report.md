# Step 5 verification report

Date: 17 November 2026

OS: Windows (win32 10.0.26200), PowerShell

## Gate results

| Check | Result | Evidence |
| --- | --- | --- |
| G1. Git clean and in sync | PASS | `main` and `origin/main` were `52c1b5a`. Log contains `0f2aa25` and `1cbef4b`. |
| G2. Step 4 files | PASS | Auth modules, proxy, login, signup, dashboard, admin, header, and the Step 4 report exist. |
| G3. Env readiness | PASS | Required backend and frontend variables are set. Both env files are gitignored. No secret values in tracked files. |
| G4. pytest, lint, build | PASS | pytest 10 passed. Frontend lint and build exited 0. |
| G5. Seeded service | PASS | `community-certificate` is active and has 5 required documents. |
| G6. Manual auth tests | PASS | Owner answered yes. |

## Step 5 checks

| Check | Result | Evidence | Reason if not PASS | Fix |
| --- | --- | --- | --- | --- |
| Gate passed | PASS | G1–G6 passed before UI code was added. | | |
| Page files created | PASS | `/`, `/services`, `/services/[slug]`, `/applications`, `/applications/[id]`, and the dashboard links exist. | | |
| Language helper | PASS | `pickName` uses `name_ta` only when the language is `ta` and that name exists. | | |
| StatusBadge | PASS | Pending, Uploaded, Processing, Passed, Needs fix, and Failed each have a text label and an icon. | | |
| Disclaimer | PASS | The required notice is on the landing page, service detail page, and checklist page. | | |
| Protected-route config | PASS | `/applications` redirects to `/login?next=...`. `/` and `/services` stay public. `getUser()` is used. `next` must start with one `/`. | | |
| lint | PASS | `npm run lint` in `frontend` exited 0. | | |
| build | PASS | `npm run build` exited 0. | | |
| pytest | PASS | `10 passed` in `backend`. No backend files were changed. | | |
| GET / | PASS | 200 | | |
| GET /services | PASS | 200 | | |
| GET /services/community-certificate | PASS | 200, and the HTML contains `Community Certificate`. | | |
| GET /services/does-not-exist | PASS | 404, and the HTML contains `Service not found`. | | |
| GET /applications logged out | PASS | 307 to `/login?next=%2Fapplications`. | | |
| GET /applications/00000000-0000-0000-0000-000000000000 logged out | PASS | 307 to `/login?next=%2Fapplications%2F00000000-0000-0000-0000-000000000000`. | | |
| GET /login | PASS | 200 | | |
| Required-document count | PASS | The page `data-required-count` is 5. The database has 5 active required documents for this service. | | |
| No secrets committed | PASS | Env files, `.venv`, and `node_modules` are not staged. | | |
| Commit and push | PASS | `9d5cb3df920b0d515408089ba2a69df52cc98d89` is on `origin/main`. | | |
| Working tree clean | PASS | Only this report remains to be committed after the UI push. | | |
| Landing page on desktop and phone width | PENDING-USER | Not viewed in a browser at two widths. | The owner must look at the page. | Open `/` on a wide window and a narrow window. |
| /services lists Community Certificate | PENDING-USER | The HTML contains the name. The card layout was not viewed. | The owner must confirm the card. | Open `/services` while signed out. |
| Service detail shows the document list and Draft indicator | PENDING-USER | The page renders 5 documents. The layout was not viewed. | The owner must read the page. | Open `/services/community-certificate`. |
| Start document check creates an application | PENDING-USER | No real row was created. | The owner must use a signed-in account. | Sign in and choose Start document check. |
| Checklist shows every document as Pending with a disabled upload slot | PENDING-USER | The slot is a disabled placeholder in code. A new application was not opened. | The owner must open a new checklist. | Open the new application and read each card. |
| Continue your draft reuses the draft | PENDING-USER | The button is shown only when a draft exists. It was not clicked. | The owner must return to the service. | Open the same service again and choose Continue your draft. |
| My applications lists and deletes applications | PENDING-USER | Delete asks for confirmation in code. It was not clicked. | The owner must try the list. | Open `/applications`, then delete a test application. |
| A second user cannot open the first user's application URL | PENDING-USER | RLS limits applications to the owner. A second account was not used. | The owner must try a second account. | Copy an application URL and open it while signed in as someone else. |
| EN / தமிழ் toggle switches document names | PENDING-USER | Names come from `pickName`. The toggle was not clicked. | The owner must switch language. | On a service page, choose தமிழ் and confirm the document names change. |
| Header menu works on a phone-sized screen | PENDING-USER | The Menu button is hidden from `md` and up. It was not tapped. | The owner must narrow the window. | Narrow the browser and open Menu. |

## Overall verdict

AI work: PASS; live UI tests: PENDING until the owner tests

## Manual test steps for the owner

1. Start the backend and frontend with the commands below.
2. Open `http://localhost:3000` on a wide window and a phone-sized window. Confirm the hero, the three steps, the reasons, the disclaimer, and the small system-status section.
3. Open `/services`. Confirm Community Certificate appears as a Draft list.
4. Open `/services/community-certificate`. Confirm the document list, the disclaimer, and Start document check.
5. While signed out, choose Start document check and confirm the login page returns you to that service.
6. Sign in, start a check, and confirm the checklist shows every required document as Pending with a disabled upload button.
7. Go back to the service and choose Continue your draft. Confirm it opens the same application.
8. Open My applications. Confirm the new row, then delete it after the confirmation.
9. Sign in as a second user and open the first user's application URL. Confirm it is not shown.
10. Use EN / தமிழ் and confirm only the service and document names change.
11. Narrow the window and confirm the header Menu opens Home, Services, and the signed-in links.

### Windows PowerShell

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000
```

In a second terminal:

```powershell
cd frontend
npm run dev
```

The site is `http://localhost:3000`. The API is `http://localhost:8000`.
