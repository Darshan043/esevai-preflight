-- Backend uses the service-role key and bypasses RLS; the frontend uses the anon key and is restricted by these policies.
-- Safe to run again: each policy is dropped before it is created.

ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.services ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.required_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.applications ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.uploaded_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.validation_results ENABLE ROW LEVEL SECURITY;

-- A user can read and edit their own profile. An admin can read every profile.
DROP POLICY IF EXISTS profiles_select_own ON public.profiles;
CREATE POLICY profiles_select_own
  ON public.profiles
  FOR SELECT
  TO authenticated
  USING (id = auth.uid());

DROP POLICY IF EXISTS profiles_update_own ON public.profiles;
CREATE POLICY profiles_update_own
  ON public.profiles
  FOR UPDATE
  TO authenticated
  USING (id = auth.uid())
  WITH CHECK (id = auth.uid());

DROP POLICY IF EXISTS profiles_admin_select ON public.profiles;
CREATE POLICY profiles_admin_select
  ON public.profiles
  FOR SELECT
  TO authenticated
  USING (public.is_admin());

-- Active services are public. Admins can manage every row, including inactive ones.
DROP POLICY IF EXISTS services_select_active ON public.services;
CREATE POLICY services_select_active
  ON public.services
  FOR SELECT
  TO anon, authenticated
  USING (is_active = true);

DROP POLICY IF EXISTS services_admin_select ON public.services;
CREATE POLICY services_admin_select
  ON public.services
  FOR SELECT
  TO authenticated
  USING (public.is_admin());

DROP POLICY IF EXISTS services_admin_insert ON public.services;
CREATE POLICY services_admin_insert
  ON public.services
  FOR INSERT
  TO authenticated
  WITH CHECK (public.is_admin());

DROP POLICY IF EXISTS services_admin_update ON public.services;
CREATE POLICY services_admin_update
  ON public.services
  FOR UPDATE
  TO authenticated
  USING (public.is_admin())
  WITH CHECK (public.is_admin());

DROP POLICY IF EXISTS services_admin_delete ON public.services;
CREATE POLICY services_admin_delete
  ON public.services
  FOR DELETE
  TO authenticated
  USING (public.is_admin());

-- Same rule as services: the public sees active checklist rows only.
DROP POLICY IF EXISTS required_documents_select_active ON public.required_documents;
CREATE POLICY required_documents_select_active
  ON public.required_documents
  FOR SELECT
  TO anon, authenticated
  USING (is_active = true);

DROP POLICY IF EXISTS required_documents_admin_select ON public.required_documents;
CREATE POLICY required_documents_admin_select
  ON public.required_documents
  FOR SELECT
  TO authenticated
  USING (public.is_admin());

DROP POLICY IF EXISTS required_documents_admin_insert ON public.required_documents;
CREATE POLICY required_documents_admin_insert
  ON public.required_documents
  FOR INSERT
  TO authenticated
  WITH CHECK (public.is_admin());

DROP POLICY IF EXISTS required_documents_admin_update ON public.required_documents;
CREATE POLICY required_documents_admin_update
  ON public.required_documents
  FOR UPDATE
  TO authenticated
  USING (public.is_admin())
  WITH CHECK (public.is_admin());

DROP POLICY IF EXISTS required_documents_admin_delete ON public.required_documents;
CREATE POLICY required_documents_admin_delete
  ON public.required_documents
  FOR DELETE
  TO authenticated
  USING (public.is_admin());

-- A citizen can manage only their own applications.
DROP POLICY IF EXISTS applications_owner_all ON public.applications;
CREATE POLICY applications_owner_all
  ON public.applications
  FOR ALL
  TO authenticated
  USING (user_id = auth.uid())
  WITH CHECK (user_id = auth.uid());

DROP POLICY IF EXISTS applications_admin_select ON public.applications;
CREATE POLICY applications_admin_select
  ON public.applications
  FOR SELECT
  TO authenticated
  USING (public.is_admin());

-- A citizen can manage only files they own, and only on their own application.
DROP POLICY IF EXISTS uploaded_documents_owner_select ON public.uploaded_documents;
CREATE POLICY uploaded_documents_owner_select
  ON public.uploaded_documents
  FOR SELECT
  TO authenticated
  USING (user_id = auth.uid());

DROP POLICY IF EXISTS uploaded_documents_owner_insert ON public.uploaded_documents;
CREATE POLICY uploaded_documents_owner_insert
  ON public.uploaded_documents
  FOR INSERT
  TO authenticated
  WITH CHECK (
    user_id = auth.uid()
    AND EXISTS (
      SELECT 1
      FROM public.applications AS applications
      WHERE applications.id = application_id
        AND applications.user_id = auth.uid()
    )
  );

DROP POLICY IF EXISTS uploaded_documents_owner_update ON public.uploaded_documents;
CREATE POLICY uploaded_documents_owner_update
  ON public.uploaded_documents
  FOR UPDATE
  TO authenticated
  USING (user_id = auth.uid())
  WITH CHECK (
    user_id = auth.uid()
    AND EXISTS (
      SELECT 1
      FROM public.applications AS applications
      WHERE applications.id = application_id
        AND applications.user_id = auth.uid()
    )
  );

DROP POLICY IF EXISTS uploaded_documents_owner_delete ON public.uploaded_documents;
CREATE POLICY uploaded_documents_owner_delete
  ON public.uploaded_documents
  FOR DELETE
  TO authenticated
  USING (user_id = auth.uid());

DROP POLICY IF EXISTS uploaded_documents_admin_select ON public.uploaded_documents;
CREATE POLICY uploaded_documents_admin_select
  ON public.uploaded_documents
  FOR SELECT
  TO authenticated
  USING (public.is_admin());

-- Citizens can read results for their own application. The backend writes results with the service-role key.
DROP POLICY IF EXISTS validation_results_owner_select ON public.validation_results;
CREATE POLICY validation_results_owner_select
  ON public.validation_results
  FOR SELECT
  TO authenticated
  USING (
    EXISTS (
      SELECT 1
      FROM public.applications AS applications
      WHERE applications.id = application_id
        AND applications.user_id = auth.uid()
    )
  );

DROP POLICY IF EXISTS validation_results_admin_select ON public.validation_results;
CREATE POLICY validation_results_admin_select
  ON public.validation_results
  FOR SELECT
  TO authenticated
  USING (public.is_admin());

-- Table grants. Row-level security still decides which rows each key can see.
GRANT SELECT ON public.services TO anon, authenticated;
GRANT SELECT ON public.required_documents TO anon, authenticated;
GRANT SELECT, UPDATE ON public.profiles TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.applications TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.uploaded_documents TO authenticated;
GRANT SELECT ON public.validation_results TO authenticated;
