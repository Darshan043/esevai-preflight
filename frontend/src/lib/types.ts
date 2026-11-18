// Row shapes from supabase/migrations/001_schema.sql.
// The pages only read the columns they need, but these types match the tables.

export type Service = {
  id: string;
  slug: string;
  name_en: string;
  name_ta: string | null;
  description: string | null;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
  updated_at: string;
};

export type RequiredDocument = {
  id: string;
  service_id: string;
  code: string;
  name_en: string;
  name_ta: string | null;
  description: string | null;
  is_mandatory: boolean;
  accepted_formats: string[];
  max_size_mb: number;
  validity_days: number | null;
  keywords: { en?: string[]; ta?: string[] };
  required_fields: unknown[];
  rules: Record<string, unknown>;
  sort_order: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type Application = {
  id: string;
  user_id: string;
  service_id: string;
  status: "draft" | "checked";
  readiness_score: number | null;
  summary: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

// Fields the browser may keep. The storage path stays on the server.
export type PublicUpload = {
  id: string;
  required_document_id: string;
  original_filename: string | null;
  mime_type: string | null;
  size_bytes: number | null;
  status: "uploaded" | "processing" | "processed" | "failed";
  quality_metrics?: Record<string, unknown>;
  ocr_text_masked?: string | null;
  extracted_fields?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type PreviewLink = {
  url: string;
  mime_type: string | null;
  expires_in: number;
};

export type UploadedDocument = {
  id: string;
  application_id: string;
  required_document_id: string;
  user_id: string;
  storage_path: string;
  original_filename: string | null;
  mime_type: string | null;
  size_bytes: number | null;
  status: "uploaded" | "processing" | "processed" | "failed";
  quality_metrics: Record<string, unknown>;
  ocr_text_masked: string | null;
  extracted_fields: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type ValidationResult = {
  id: string;
  application_id: string;
  uploaded_document_id: string | null;
  check_code: string;
  check_name: string | null;
  status: "pass" | "warning" | "fail";
  message: string | null;
  fix_suggestion: string | null;
  details: Record<string, unknown>;
  created_at: string;
};
