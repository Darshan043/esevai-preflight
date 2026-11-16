# Step 3 verification report

**Project:** e-Sevai Pre-Flight – AI-Powered Government Document Readiness Assistant

**Date:** 16 November 2026

**Scope:** SQL files and documentation only. No connection to Supabase. No application code.

## Checks

| Check | Result | Evidence | Reason if not PASS | Fix |
| --- | --- | --- | --- | --- |
| `supabase/migrations/001_schema.sql` exists | PASS | File is in commit `279cdbb`. It creates the six tables, indexes, `set_updated_at`, `handle_new_user`, `is_admin`, the role-protection trigger, and the profile backfill. | | |
| `supabase/migrations/002_rls_policies.sql` exists | PASS | File is in commit `279cdbb`. RLS is enabled on all six tables. Owners and admins have the policies from the task. `validation_results` has SELECT only. | | |
| `supabase/migrations/003_storage.sql` exists | PASS | File is in commit `279cdbb`. Private bucket `documents`, 5,242,880 byte limit, JPEG/PNG/PDF. Owner-folder policies only. | | |
| `supabase/seed/seed_service1.sql` exists | PASS | File is in commit `279cdbb`. Upserts slug `community-certificate` and five required documents. | | |
| `supabase/scripts/promote_admin.sql` exists | PASS | File is in commit `279cdbb`. Placeholder email is `REPLACE_WITH_YOUR_EMAIL`. | | |
| `supabase/verify_step3.sql` exists | PASS | File is in commit `279cdbb`. One SELECT of `check_name` and `result`, ordered so FAIL rows come first. | | |
| Static review done | PASS | Re-read the SQL for dependency order, unique policy names, re-run safety (`IF NOT EXISTS`, `CREATE OR REPLACE`, `DROP POLICY IF EXISTS`, `ON CONFLICT`), and no full ID columns. Seed alias columns were given explicit types. The bucket privacy check uses `buckets.public = false`. | | |
| Seed read from `docs/service1-documents.md` | PASS | The source lists five real document names. Formats, mandatory flags, expiry, and key fields are not specified, and DNC is an unresolved FAQ vs Service List difference. Seed uses those five names, sets `is_verified` to false, starts the description with `DRAFT – verify against the official e-Sevai portal`, and stores DNC as not mandatory. Quality rules and accepted formats are app defaults. | | |
| Docs created | PASS | `docs/database-design.md` and `docs/step-03-run-order.md` are in commit `279cdbb`. | | |
| README updated | PASS | Status is `Step 3 – database SQL files ready (pending run in Supabase)`. A Database section links both docs. `docs/SETUP_CHECKLIST.md` marks Step 3 files as created and not run. | | |
| No secrets | PASS | Staged files are SQL and docs. No `.env`, keys, or passwords. The admin script contains only the placeholder `REPLACE_WITH_YOUR_EMAIL`. | | |
| Commit and push succeeded | PASS | `279cdbb1032fcf3e2ff829c1f98e3c6c95471c41` — `Step 3: database schema, RLS, storage and seed SQL`. Push updated `92c0b76..279cdbb` on `origin/main`. | | |
| Working tree clean | PASS | After that push, `main` matched `origin/main` with no leftover schema files. This report is a separate commit. | | |
| SQL 001 executed in Supabase | PENDING-USER | Not run from this session. | The owner runs it in the Supabase SQL Editor. | Run `supabase/migrations/001_schema.sql`. |
| SQL 002 executed in Supabase | PENDING-USER | Not run from this session. | The owner runs it after 001. | Run `supabase/migrations/002_rls_policies.sql`. |
| SQL 003 executed in Supabase | PENDING-USER | Not run from this session. | The owner runs it after 002. | Run `supabase/migrations/003_storage.sql`. |
| Seed executed | PENDING-USER | Not run from this session. | The owner runs it after 003. | Run `supabase/seed/seed_service1.sql`. |
| Admin promoted | PENDING-USER | Script still has the placeholder email. | A dashboard user must exist before promotion. | Add the user, replace the email, then run `supabase/scripts/promote_admin.sql`. |
| `verify_step3.sql` all PASS | PENDING-USER | The query has not been executed. | Database objects do not exist until the scripts above are run. | Run `supabase/verify_step3.sql` and confirm every row is PASS. |

## Overall verdict

AI work: PASS; database execution: PENDING until the owner runs the SQL

## What the owner must do now

1. Open the Supabase SQL Editor and run `supabase/migrations/001_schema.sql`. Expect success and no error. The six tables, helper functions, and triggers exist. Existing users receive a citizen profile.
2. Run `supabase/migrations/002_rls_policies.sql`. Expect success. Row-level security is on for all six tables, and the policies are created.
3. Run `supabase/migrations/003_storage.sql`. Expect success. The private bucket `documents` exists, with a 5 MB limit and JPEG, PNG, and PDF types.
4. Run `supabase/seed/seed_service1.sql`. Expect success. The `community-certificate` service is stored with `is_verified = false`, and five checklist rows are stored.
5. Create the login in Supabase Dashboard > Authentication > Users > Add user. Tick **Auto Confirm User**. Use an email address you control. Do not put that email in Git.
6. In `supabase/scripts/promote_admin.sql`, replace `REPLACE_WITH_YOUR_EMAIL` with that email, then run the script. The final SELECT shows that email with role `admin`.
7. Run `supabase/verify_step3.sql`. Every row should be `PASS`, including `at least one admin profile exists`. Before step 6, that one row is `PENDING` and the rest should already be `PASS`.
