-- Run after the migrations, the seed, and the admin promotion.
-- This does not change data. FAIL rows are listed first.
-- A missing admin is PENDING, not FAIL, until promote_admin.sql has been run.

SELECT check_name, result
FROM (
  SELECT 'table profiles exists' AS check_name,
    CASE WHEN to_regclass('public.profiles') IS NOT NULL THEN 'PASS' ELSE 'FAIL' END AS result
  UNION ALL
  SELECT 'table services exists',
    CASE WHEN to_regclass('public.services') IS NOT NULL THEN 'PASS' ELSE 'FAIL' END
  UNION ALL
  SELECT 'table required_documents exists',
    CASE WHEN to_regclass('public.required_documents') IS NOT NULL THEN 'PASS' ELSE 'FAIL' END
  UNION ALL
  SELECT 'table applications exists',
    CASE WHEN to_regclass('public.applications') IS NOT NULL THEN 'PASS' ELSE 'FAIL' END
  UNION ALL
  SELECT 'table uploaded_documents exists',
    CASE WHEN to_regclass('public.uploaded_documents') IS NOT NULL THEN 'PASS' ELSE 'FAIL' END
  UNION ALL
  SELECT 'table validation_results exists',
    CASE WHEN to_regclass('public.validation_results') IS NOT NULL THEN 'PASS' ELSE 'FAIL' END
  UNION ALL
  SELECT 'RLS enabled on profiles',
    CASE WHEN EXISTS (
      SELECT 1 FROM pg_class AS class
      JOIN pg_namespace AS namespace ON namespace.oid = class.relnamespace
      WHERE namespace.nspname = 'public' AND class.relname = 'profiles' AND class.relrowsecurity
    ) THEN 'PASS' ELSE 'FAIL' END
  UNION ALL
  SELECT 'RLS enabled on services',
    CASE WHEN EXISTS (
      SELECT 1 FROM pg_class AS class
      JOIN pg_namespace AS namespace ON namespace.oid = class.relnamespace
      WHERE namespace.nspname = 'public' AND class.relname = 'services' AND class.relrowsecurity
    ) THEN 'PASS' ELSE 'FAIL' END
  UNION ALL
  SELECT 'RLS enabled on required_documents',
    CASE WHEN EXISTS (
      SELECT 1 FROM pg_class AS class
      JOIN pg_namespace AS namespace ON namespace.oid = class.relnamespace
      WHERE namespace.nspname = 'public' AND class.relname = 'required_documents' AND class.relrowsecurity
    ) THEN 'PASS' ELSE 'FAIL' END
  UNION ALL
  SELECT 'RLS enabled on applications',
    CASE WHEN EXISTS (
      SELECT 1 FROM pg_class AS class
      JOIN pg_namespace AS namespace ON namespace.oid = class.relnamespace
      WHERE namespace.nspname = 'public' AND class.relname = 'applications' AND class.relrowsecurity
    ) THEN 'PASS' ELSE 'FAIL' END
  UNION ALL
  SELECT 'RLS enabled on uploaded_documents',
    CASE WHEN EXISTS (
      SELECT 1 FROM pg_class AS class
      JOIN pg_namespace AS namespace ON namespace.oid = class.relnamespace
      WHERE namespace.nspname = 'public' AND class.relname = 'uploaded_documents' AND class.relrowsecurity
    ) THEN 'PASS' ELSE 'FAIL' END
  UNION ALL
  SELECT 'RLS enabled on validation_results',
    CASE WHEN EXISTS (
      SELECT 1 FROM pg_class AS class
      JOIN pg_namespace AS namespace ON namespace.oid = class.relnamespace
      WHERE namespace.nspname = 'public' AND class.relname = 'validation_results' AND class.relrowsecurity
    ) THEN 'PASS' ELSE 'FAIL' END
  UNION ALL
  SELECT 'policy exists on profiles',
    CASE WHEN EXISTS (
      SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'profiles'
    ) THEN 'PASS' ELSE 'FAIL' END
  UNION ALL
  SELECT 'policy exists on services',
    CASE WHEN EXISTS (
      SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'services'
    ) THEN 'PASS' ELSE 'FAIL' END
  UNION ALL
  SELECT 'policy exists on required_documents',
    CASE WHEN EXISTS (
      SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'required_documents'
    ) THEN 'PASS' ELSE 'FAIL' END
  UNION ALL
  SELECT 'policy exists on applications',
    CASE WHEN EXISTS (
      SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'applications'
    ) THEN 'PASS' ELSE 'FAIL' END
  UNION ALL
  SELECT 'policy exists on uploaded_documents',
    CASE WHEN EXISTS (
      SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'uploaded_documents'
    ) THEN 'PASS' ELSE 'FAIL' END
  UNION ALL
  SELECT 'policy exists on validation_results',
    CASE WHEN EXISTS (
      SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'validation_results'
    ) THEN 'PASS' ELSE 'FAIL' END
  UNION ALL
  SELECT 'new-user profile trigger exists',
    CASE WHEN EXISTS (
      SELECT 1
      FROM pg_trigger AS trigger
      JOIN pg_class AS class ON class.oid = trigger.tgrelid
      JOIN pg_namespace AS namespace ON namespace.oid = class.relnamespace
      WHERE namespace.nspname = 'auth'
        AND class.relname = 'users'
        AND trigger.tgname = 'on_auth_user_created'
        AND NOT trigger.tgisinternal
    ) THEN 'PASS' ELSE 'FAIL' END
  UNION ALL
  SELECT 'is_admin function exists',
    CASE WHEN EXISTS (
      SELECT 1
      FROM pg_proc AS proc
      JOIN pg_namespace AS namespace ON namespace.oid = proc.pronamespace
      WHERE namespace.nspname = 'public'
        AND proc.proname = 'is_admin'
    ) THEN 'PASS' ELSE 'FAIL' END
  UNION ALL
  SELECT 'role-protection trigger exists',
    CASE WHEN EXISTS (
      SELECT 1
      FROM pg_trigger AS trigger
      JOIN pg_class AS class ON class.oid = trigger.tgrelid
      JOIN pg_namespace AS namespace ON namespace.oid = class.relnamespace
      WHERE namespace.nspname = 'public'
        AND class.relname = 'profiles'
        AND trigger.tgname = 'profiles_block_role_change'
        AND NOT trigger.tgisinternal
    ) THEN 'PASS' ELSE 'FAIL' END
  UNION ALL
  SELECT 'documents bucket exists and is private',
    CASE WHEN EXISTS (
      SELECT 1
      FROM storage.buckets AS buckets
      WHERE buckets.id = 'documents'
        AND buckets.public = false
    ) THEN 'PASS' ELSE 'FAIL' END
  UNION ALL
  SELECT 'documents storage policies exist',
    CASE WHEN (
      SELECT count(*)
      FROM pg_policies
      WHERE schemaname = 'storage'
        AND tablename = 'objects'
        AND policyname IN (
          'documents_select_own',
          'documents_insert_own',
          'documents_update_own',
          'documents_delete_own'
        )
    ) = 4 THEN 'PASS' ELSE 'FAIL' END
  UNION ALL
  SELECT 'service community-certificate exists',
    CASE WHEN EXISTS (
      SELECT 1 FROM public.services WHERE slug = 'community-certificate'
    ) THEN 'PASS' ELSE 'FAIL' END
  UNION ALL
  SELECT 'community-certificate has at least 3 documents',
    CASE WHEN (
      SELECT count(*)
      FROM public.required_documents AS documents
      JOIN public.services AS services ON services.id = documents.service_id
      WHERE services.slug = 'community-certificate'
    ) >= 3 THEN 'PASS' ELSE 'FAIL' END
  UNION ALL
  SELECT 'at least one admin profile exists',
    CASE
      WHEN to_regclass('public.profiles') IS NULL THEN 'FAIL'
      WHEN EXISTS (SELECT 1 FROM public.profiles WHERE role = 'admin') THEN 'PASS'
      ELSE 'PENDING'
    END
) AS checks
ORDER BY
  CASE result WHEN 'FAIL' THEN 0 WHEN 'PENDING' THEN 1 ELSE 2 END,
  check_name;
