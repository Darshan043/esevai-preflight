// Server-only reads and writes through the signed-in user's Supabase session.
// Row level security decides what each person can see. Do not import this from client components.

import { connection } from "next/server";

import { LANGUAGE_COOKIE, parseLanguage, type Language } from "@/lib/language";
import { createClient, getUserAndProfile } from "@/lib/supabase/server";
import { isReadinessLabel } from "@/lib/report";
import { uniqueById } from "@/lib/unique";
import type {
  Application,
  ReadinessLabel,
  RequiredDocument,
  Service,
  UploadedDocument,
  ValidationResult,
} from "@/lib/types";

const friendlyError = "We could not load this page. Check your connection and try again.";

export type ServiceListItem = Pick<
  Service,
  "id" | "slug" | "name_en" | "name_ta" | "description" | "is_verified"
> & { documentCount: number };

export type ApplicationListItem = Pick<
  Application,
  "id" | "status" | "readiness_score" | "created_at"
> & {
  serviceName: { name_en: string; name_ta: string | null };
  uploadedCount: number;
  requiredCount: number;
  label: ReadinessLabel | null;
};

async function client() {
  await connection();
  return createClient();
}

export async function getRequestLanguage(): Promise<Language> {
  await connection();
  const current = await getUserAndProfile();
  const profileLanguage = current?.profile?.preferred_language;
  if (profileLanguage === "en" || profileLanguage === "ta") {
    return profileLanguage;
  }
  const { cookies } = await import("next/headers");
  const store = await cookies();
  return parseLanguage(store.get(LANGUAGE_COOKIE)?.value);
}

export async function listServices(): Promise<{ items: ServiceListItem[]; error: string | null }> {
  try {
    const supabase = await client();
    const { data, error } = await supabase
      .from("services")
      .select("id, slug, name_en, name_ta, description, is_verified, required_documents(id, is_active)")
      .eq("is_active", true)
      .order("name_en");

    if (error) {
      return { items: [], error: friendlyError };
    }

    const items = (data ?? []).map((row) => {
      const documents = Array.isArray(row.required_documents) ? row.required_documents : [];
      return {
        id: row.id,
        slug: row.slug,
        name_en: row.name_en,
        name_ta: row.name_ta,
        description: row.description,
        is_verified: row.is_verified,
        documentCount: documents.filter((document) => document.is_active).length,
      };
    });
    return { items, error: null };
  } catch {
    return { items: [], error: friendlyError };
  }
}

export async function getServiceBySlug(slug: string): Promise<{
  service: Pick<Service, "id" | "slug" | "name_en" | "name_ta" | "description" | "is_verified"> | null;
  documents: RequiredDocument[];
  error: string | null;
}> {
  try {
    const supabase = await client();
    const { data, error } = await supabase
      .from("services")
      .select("id, slug, name_en, name_ta, description, is_verified")
      .eq("slug", slug)
      .eq("is_active", true)
      .maybeSingle();

    if (error) {
      return { service: null, documents: [], error: friendlyError };
    }
    if (!data) {
      return { service: null, documents: [], error: null };
    }

    const documentsResult = await supabase
      .from("required_documents")
      .select(
        "id, service_id, code, name_en, name_ta, description, is_mandatory, accepted_formats, max_size_mb, validity_days, keywords, required_fields, rules, sort_order, is_active, created_at, updated_at",
      )
      .eq("service_id", data.id)
      .eq("is_active", true)
      .order("sort_order");

    if (documentsResult.error) {
      return { service: null, documents: [], error: friendlyError };
    }

    return {
      service: data,
      documents: (documentsResult.data ?? []) as RequiredDocument[],
      error: null,
    };
  } catch {
    return { service: null, documents: [], error: friendlyError };
  }
}

export async function latestDraftId(serviceId: string, userId: string): Promise<string | null> {
  const supabase = await client();
  const { data } = await supabase
    .from("applications")
    .select("id")
    .eq("service_id", serviceId)
    .eq("user_id", userId)
    .eq("status", "draft")
    .order("created_at", { ascending: false })
    .limit(1)
    .maybeSingle();
  return data?.id ?? null;
}

export async function listMyApplications(): Promise<{
  items: ApplicationListItem[];
  error: string | null;
}> {
  try {
    const supabase = await client();
    const { data, error } = await supabase
      .from("applications")
      .select(
        "id, status, readiness_score, created_at, summary, services(name_en, name_ta, required_documents(id, is_active)), uploaded_documents(id, required_document_id)",
      )
      .order("created_at", { ascending: false });

    if (error) {
      return { items: [], error: friendlyError };
    }

    const items = uniqueById(
      (data ?? []).map((row) => {
        const service = Array.isArray(row.services) ? row.services[0] : row.services;
        const required = Array.isArray(service?.required_documents) ? service.required_documents : [];
        const activeIds = new Set(
          required.filter((document) => document.is_active).map((document) => document.id),
        );
        const uploads = Array.isArray(row.uploaded_documents) ? row.uploaded_documents : [];
        return {
          id: row.id,
          status: row.status,
          readiness_score: row.readiness_score,
          label: labelFromSummary(row.summary),
          created_at: row.created_at,
          serviceName: {
            name_en: service?.name_en ?? "Service",
            name_ta: service?.name_ta ?? null,
          },
          uploadedCount: uploads.filter((upload) => activeIds.has(upload.required_document_id)).length,
          requiredCount: activeIds.size,
        };
      }),
    );
    return { items, error: null };
  } catch {
    return { items: [], error: friendlyError };
  }
}

export async function countMyApplications(): Promise<number> {
  const supabase = await client();
  const { count } = await supabase.from("applications").select("id", { count: "exact", head: true });
  return count ?? 0;
}

export async function latestReadiness(): Promise<{ score: number; label: ReadinessLabel } | null> {
  const supabase = await client();
  const { data, error } = await supabase
    .from("applications")
    .select("readiness_score, summary, updated_at")
    .not("readiness_score", "is", null)
    .eq("status", "checked")
    .order("updated_at", { ascending: false })
    .limit(1)
    .maybeSingle();
  if (error || !data || typeof data.readiness_score !== "number") {
    return null;
  }
  const label = labelFromSummary(data.summary);
  if (!label) {
    return { score: data.readiness_score, label: "not_ready" };
  }
  return { score: data.readiness_score, label };
}

function labelFromSummary(summary: unknown): ReadinessLabel | null {
  if (!summary || typeof summary !== "object") {
    return null;
  }
  const report = (summary as { report?: { label?: unknown } }).report;
  if (!report || typeof report !== "object") {
    return null;
  }
  return isReadinessLabel(report.label) ? report.label : null;
}

export type ChecklistData = {
  application: Pick<Application, "id" | "status" | "readiness_score">;
  service: Pick<Service, "name_en" | "name_ta" | "description" | "slug">;
  documents: RequiredDocument[];
  uploads: UploadedDocument[];
  results: ValidationResult[];
};

export async function getChecklist(applicationId: string): Promise<{
  data: ChecklistData | null;
  error: string | null;
}> {
  try {
    const supabase = await client();
    const { data, error } = await supabase
      .from("applications")
      .select("id, status, readiness_score, service_id, services(name_en, name_ta, description, slug)")
      .eq("id", applicationId)
      .maybeSingle();

    if (error) {
      return { data: null, error: friendlyError };
    }
    if (!data) {
      return { data: null, error: null };
    }

    const service = Array.isArray(data.services) ? data.services[0] : data.services;
    if (!service) {
      return { data: null, error: null };
    }

    const [documentsResult, uploadsResult, resultsResult] = await Promise.all([
      supabase
        .from("required_documents")
        .select(
          "id, service_id, code, name_en, name_ta, description, is_mandatory, accepted_formats, max_size_mb, validity_days, keywords, required_fields, rules, sort_order, is_active, created_at, updated_at",
        )
        .eq("service_id", data.service_id)
        .eq("is_active", true)
        .order("sort_order"),
      supabase
        .from("uploaded_documents")
        .select(
          "id, application_id, required_document_id, user_id, storage_path, original_filename, mime_type, size_bytes, status, quality_metrics, ocr_text_masked, extracted_fields, created_at, updated_at",
        )
        .eq("application_id", data.id),
      supabase
        .from("validation_results")
        .select(
          "id, application_id, uploaded_document_id, check_code, check_name, status, message, fix_suggestion, details, created_at",
        )
        .eq("application_id", data.id),
    ]);

    if (documentsResult.error || uploadsResult.error || resultsResult.error) {
      return { data: null, error: friendlyError };
    }

    return {
      data: {
        application: {
          id: data.id,
          status: data.status,
          readiness_score: data.readiness_score,
        },
        service,
        documents: (documentsResult.data ?? []) as RequiredDocument[],
        uploads: (uploadsResult.data ?? []) as UploadedDocument[],
        results: (resultsResult.data ?? []) as ValidationResult[],
      },
      error: null,
    };
  } catch {
    return { data: null, error: friendlyError };
  }
}
