-- Step 3 schema for e-Sevai Pre-Flight.
-- Safe to run again. Existing tables are left in place (IF NOT EXISTS does not change columns).

-- profiles: one row per signed-in user. Role starts as citizen and cannot be self-promoted.
CREATE TABLE IF NOT EXISTS public.profiles (
  id uuid PRIMARY KEY REFERENCES auth.users (id) ON DELETE CASCADE,
  full_name text,
  role text NOT NULL DEFAULT 'citizen' CHECK (role IN ('citizen', 'admin')),
  preferred_language text NOT NULL DEFAULT 'en' CHECK (preferred_language IN ('en', 'ta')),
  created_at timestamptz NOT NULL DEFAULT now()
);

-- services: a government service the citizen can prepare for, such as Community Certificate.
CREATE TABLE IF NOT EXISTS public.services (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  slug text UNIQUE NOT NULL,
  name_en text NOT NULL,
  name_ta text,
  description text,
  is_active boolean NOT NULL DEFAULT true,
  -- true only after the document list is checked against the official portal.
  is_verified boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

-- required_documents: the checklist items for one service.
-- Store masked values and extracted JSON later. Never add a column for a full ID number.
CREATE TABLE IF NOT EXISTS public.required_documents (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  service_id uuid NOT NULL REFERENCES public.services (id) ON DELETE CASCADE,
  code text NOT NULL,
  name_en text NOT NULL,
  name_ta text,
  description text,
  is_mandatory boolean NOT NULL DEFAULT true,
  accepted_formats text[] NOT NULL DEFAULT '{jpg,jpeg,png,pdf}',
  max_size_mb int NOT NULL DEFAULT 5,
  validity_days int,
  keywords jsonb NOT NULL DEFAULT '{"en":[],"ta":[]}',
  required_fields jsonb NOT NULL DEFAULT '[]',
  rules jsonb NOT NULL DEFAULT '{}',
  sort_order int NOT NULL DEFAULT 0,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (service_id, code)
);

-- applications: one citizen's draft check for one service.
CREATE TABLE IF NOT EXISTS public.applications (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES public.profiles (id) ON DELETE CASCADE,
  service_id uuid NOT NULL REFERENCES public.services (id),
  status text NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'checked')),
  readiness_score int CHECK (readiness_score BETWEEN 0 AND 100),
  summary jsonb NOT NULL DEFAULT '{}',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

-- uploaded_documents: the file the citizen attached for one checklist item.
-- ocr_text_masked and extracted_fields must not contain a full Aadhaar or ID number.
CREATE TABLE IF NOT EXISTS public.uploaded_documents (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  application_id uuid NOT NULL REFERENCES public.applications (id) ON DELETE CASCADE,
  required_document_id uuid NOT NULL REFERENCES public.required_documents (id),
  user_id uuid NOT NULL REFERENCES public.profiles (id) ON DELETE CASCADE,
  storage_path text NOT NULL,
  original_filename text,
  mime_type text,
  size_bytes bigint,
  status text NOT NULL DEFAULT 'uploaded' CHECK (status IN ('uploaded', 'processing', 'processed', 'failed')),
  quality_metrics jsonb NOT NULL DEFAULT '{}',
  ocr_text_masked text,
  extracted_fields jsonb NOT NULL DEFAULT '{}',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (application_id, required_document_id)
);

-- validation_results: one check result. uploaded_document_id is null for a cross-document check.
CREATE TABLE IF NOT EXISTS public.validation_results (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  application_id uuid NOT NULL REFERENCES public.applications (id) ON DELETE CASCADE,
  uploaded_document_id uuid REFERENCES public.uploaded_documents (id) ON DELETE CASCADE,
  check_code text NOT NULL,
  check_name text,
  status text NOT NULL CHECK (status IN ('pass', 'warning', 'fail')),
  message text,
  fix_suggestion text,
  details jsonb NOT NULL DEFAULT '{}',
  created_at timestamptz NOT NULL DEFAULT now()
);

-- Indexes for the foreign keys the app will filter on.
CREATE INDEX IF NOT EXISTS required_documents_service_id_idx ON public.required_documents (service_id);
CREATE INDEX IF NOT EXISTS applications_user_id_idx ON public.applications (user_id);
CREATE INDEX IF NOT EXISTS applications_service_id_idx ON public.applications (service_id);
CREATE INDEX IF NOT EXISTS uploaded_documents_application_id_idx ON public.uploaded_documents (application_id);
CREATE INDEX IF NOT EXISTS uploaded_documents_required_document_id_idx ON public.uploaded_documents (required_document_id);
CREATE INDEX IF NOT EXISTS uploaded_documents_user_id_idx ON public.uploaded_documents (user_id);
CREATE INDEX IF NOT EXISTS validation_results_application_id_idx ON public.validation_results (application_id);
CREATE INDEX IF NOT EXISTS validation_results_uploaded_document_id_idx ON public.validation_results (uploaded_document_id);

-- Keeps updated_at current whenever a row changes.
CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = public
AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS services_set_updated_at ON public.services;
CREATE TRIGGER services_set_updated_at
  BEFORE UPDATE ON public.services
  FOR EACH ROW
  EXECUTE FUNCTION public.set_updated_at();

DROP TRIGGER IF EXISTS required_documents_set_updated_at ON public.required_documents;
CREATE TRIGGER required_documents_set_updated_at
  BEFORE UPDATE ON public.required_documents
  FOR EACH ROW
  EXECUTE FUNCTION public.set_updated_at();

DROP TRIGGER IF EXISTS applications_set_updated_at ON public.applications;
CREATE TRIGGER applications_set_updated_at
  BEFORE UPDATE ON public.applications
  FOR EACH ROW
  EXECUTE FUNCTION public.set_updated_at();

DROP TRIGGER IF EXISTS uploaded_documents_set_updated_at ON public.uploaded_documents;
CREATE TRIGGER uploaded_documents_set_updated_at
  BEFORE UPDATE ON public.uploaded_documents
  FOR EACH ROW
  EXECUTE FUNCTION public.set_updated_at();

-- True when the signed-in user is an admin.
-- SECURITY DEFINER avoids recursive row-level security when policies call this function.
CREATE OR REPLACE FUNCTION public.is_admin()
RETURNS boolean
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT EXISTS (
    SELECT 1
    FROM public.profiles
    WHERE id = auth.uid()
      AND role = 'admin'
  );
$$;

-- Creates a citizen profile when Supabase Auth adds a user.
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  INSERT INTO public.profiles (id, full_name, role)
  VALUES (
    NEW.id,
    NULLIF(NEW.raw_user_meta_data->>'full_name', ''),
    'citizen'
  )
  ON CONFLICT (id) DO NOTHING;

  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW
  EXECUTE FUNCTION public.handle_new_user();

-- Citizens cannot change their own role to admin.
-- auth.uid() is null in the SQL Editor and for the service role, so those paths can still set a role.
CREATE OR REPLACE FUNCTION public.prevent_role_change()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = public
AS $$
BEGIN
  IF NEW.role IS DISTINCT FROM OLD.role THEN
    IF auth.uid() IS NOT NULL AND NOT public.is_admin() THEN
      RAISE EXCEPTION 'Only an admin can change a profile role';
    END IF;
  END IF;

  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS profiles_block_role_change ON public.profiles;
CREATE TRIGGER profiles_block_role_change
  BEFORE UPDATE ON public.profiles
  FOR EACH ROW
  EXECUTE FUNCTION public.prevent_role_change();

-- Profiles for accounts that already existed before this script.
INSERT INTO public.profiles (id, full_name, role)
SELECT
  users.id,
  NULLIF(users.raw_user_meta_data->>'full_name', ''),
  'citizen'
FROM auth.users AS users
WHERE NOT EXISTS (
  SELECT 1
  FROM public.profiles AS profiles
  WHERE profiles.id = users.id
)
ON CONFLICT (id) DO NOTHING;
