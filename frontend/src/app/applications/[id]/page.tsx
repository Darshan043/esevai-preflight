import { notFound, redirect } from "next/navigation";
import { Suspense } from "react";

import { ChecklistBoard, type ChecklistSlot } from "@/components/ChecklistBoard";
import { ErrorMessage } from "@/components/ErrorMessage";
import { LoadingSkeleton } from "@/components/LoadingSkeleton";
import { PageContainer } from "@/components/PageContainer";
import { getChecklist, getRequestLanguage } from "@/lib/catalog";
import { pickName } from "@/lib/language";
import { getUserAndProfile } from "@/lib/supabase/server";
import type { PublicUpload } from "@/lib/types";

function validityText(days: number | null): string | null {
  if (days == null) {
    return null;
  }
  return days === 1
    ? "Use a document from the last 1 day."
    : `Use a document from the last ${days} days.`;
}

function publicUpload(upload: {
  id: string;
  required_document_id: string;
  original_filename: string | null;
  mime_type: string | null;
  size_bytes: number | null;
  status: PublicUpload["status"];
  quality_metrics: Record<string, unknown> | null;
  ocr_text_masked: string | null;
  extracted_fields?: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}): PublicUpload {
  return {
    id: upload.id,
    required_document_id: upload.required_document_id,
    original_filename: upload.original_filename,
    mime_type: upload.mime_type,
    size_bytes: upload.size_bytes,
    status: upload.status,
    quality_metrics: upload.quality_metrics ?? {},
    ocr_text_masked: upload.ocr_text_masked,
    extracted_fields: upload.extracted_fields ?? {},
    created_at: upload.created_at,
    updated_at: upload.updated_at,
  };
}

async function Checklist({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const current = await getUserAndProfile();
  if (!current) {
    redirect(`/login?next=/applications/${id}`);
  }

  const [language, result] = await Promise.all([getRequestLanguage(), getChecklist(id)]);
  if (result.error) {
    return <ErrorMessage message={result.error} />;
  }
  if (!result.data) {
    notFound();
  }

  const { service, documents, uploads, results, application } = result.data;
  const slots: ChecklistSlot[] = documents.map((document) => {
    const upload = uploads.find((item) => item.required_document_id === document.id) ?? null;
    return {
      id: document.id,
      name: pickName(document, language),
      description: document.description,
      isMandatory: document.is_mandatory,
      acceptedFormats: document.accepted_formats,
      maxSizeMb: document.max_size_mb,
      validity: validityText(document.validity_days),
      upload: upload ? publicUpload(upload) : null,
    };
  });

  return (
    <ChecklistBoard
      applicationId={application.id}
      title={pickName(service, language)}
      statusLabel={application.status === "checked" ? "Checked" : "Draft"}
      slots={slots}
      results={results}
      language={language}
      serviceSlug={service.slug}
    />
  );
}

export default function ApplicationPage({ params }: { params: Promise<{ id: string }> }) {
  return (
    <PageContainer className="checklist-workspace">
      <Suspense fallback={<LoadingSkeleton label="Loading checklist" />}>
        <Checklist params={params} />
      </Suspense>
    </PageContainer>
  );
}
