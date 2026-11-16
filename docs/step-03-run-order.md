# Step 3 run order

Run these in the Supabase SQL Editor, in this order. Run each file as one script. Do not skip ahead.

1. `supabase/migrations/001_schema.sql`
   Expected result: success, with no error. The six tables, helper functions, and triggers exist. Existing users receive a citizen profile.

2. `supabase/migrations/002_rls_policies.sql`
   Expected result: success. Row-level security is on for all six tables, and the policies are created.

3. `supabase/migrations/003_storage.sql`
   Expected result: success. The private bucket `documents` exists, with a 5 MB limit and JPEG, PNG, and PDF types.

4. `supabase/seed/seed_service1.sql`
   Expected result: success. The `community-certificate` service is stored with `is_verified = false`, and five checklist rows are stored.

5. Create your login in the dashboard before the next script.
   Supabase Dashboard > Authentication > Users > Add user. Tick **Auto Confirm User**. Use the email address you control. Do not put that email in Git.

6. `supabase/scripts/promote_admin.sql`
   Expected result: before running, replace `REPLACE_WITH_YOUR_EMAIL` with the email from step 5. The final SELECT shows that email with role `admin`.

7. `supabase/verify_step3.sql`
   Expected result: every row is `PASS`, including `at least one admin profile exists`. Before step 6, that one row is `PENDING` and the rest should already be `PASS`.
