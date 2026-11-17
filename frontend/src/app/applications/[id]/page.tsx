import { notFound, redirect } from "next/navigation";
import { Suspense } from "react";

import { Card } from "@/components/Card";
import { Disclaimer } from "@/components/Disclaimer";
import { ErrorMessage } from "@/components/ErrorMessage";
import { LoadingSkeleton } from "@/components/LoadingSkeleton";
import { PageContainer } from "@/components/PageContainer";
import { StatusBadge } from "@/components/StatusBadge";
import { getChecklist, getRequestLanguage } from "@/lib/catalog";
import { pickName } from "@/lib/language";
import { slotStatus } from "@/lib/slot-status";
import { getUserAndProfile } from "@/lib/supabase/server";

function formatBytes(bytes: number | null): string {
  if (bytes == null) {
    return "Size not recorded";
  }
  if (bytes < 1024) {
    return `${bytes} B`;
  }
  if (bytes < 1024 * 1024) {
    return `${Math.round(bytes / 1024)} KB`;
  }
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function validityText(days: number | null): string | null {
  if (days == null) {
    return null;
  }
  return days === 1
    ? "Use a document from the last 1 day."
    : `Use a document from the last ${days} days.`;
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
  const uploadedCount = documents.filter((document) =>
    uploads.some((upload) => upload.required_document_id === document.id),
  ).length;
  const progress = documents.length === 0 ? 0 : Math.round((uploadedCount / documents.length) * 100);

  return (
    <>
      <header className="flex flex-col gap-3">
        <h1 className="text-3xl font-semibold tracking-tight text-zinc-900">{pickName(service, language)}</h1>
        <p className="text-sm text-zinc-700">
          Application status: {application.status === "checked" ? "Checked" : "Draft"}
        </p>
        <div>
          <p className="text-sm font-medium text-zinc-800" id="upload-progress-label">
            {uploadedCount} of {documents.length} required documents uploaded
          </p>
          <div
            className="mt-2 h-3 overflow-hidden rounded-full bg-zinc-200"
            role="progressbar"
            aria-labelledby="upload-progress-label"
            aria-valuemin={0}
            aria-valuemax={documents.length}
            aria-valuenow={uploadedCount}
          >
            <div className="h-full bg-zinc-900" style={{ width: `${progress}%` }} />
          </div>
        </div>
      </header>
      <Disclaimer />
      <ul className="flex flex-col gap-4" data-required-count={documents.length}>
        {documents.map((document) => {
          const upload = uploads.find((item) => item.required_document_id === document.id) ?? null;
          const status = slotStatus(upload, results);
          const validity = validityText(document.validity_days);
          return (
            <li key={document.id}>
              <Card>
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <h2 className="text-xl font-semibold text-zinc-900">{pickName(document, language)}</h2>
                  <StatusBadge status={status} />
                </div>
                <p className="mt-2 text-sm font-medium text-zinc-700">
                  {document.is_mandatory ? "Mandatory" : "Optional"}
                </p>
                {document.description ? (
                  <p className="mt-2 text-zinc-600">Tip: {document.description}</p>
                ) : null}
                <p className="mt-2 text-sm text-zinc-700">
                  Accepted formats: {document.accepted_formats.join(", ")}
                </p>
                <p className="mt-1 text-sm text-zinc-700">Maximum size: {document.max_size_mb} MB</p>
                {validity ? <p className="mt-1 text-sm text-zinc-700">{validity}</p> : null}
                {upload ? (
                  <div className="mt-4 rounded-lg border border-zinc-200 bg-zinc-50 p-4 text-sm text-zinc-800">
                    <p>File: {upload.original_filename ?? "Uploaded file"}</p>
                    <p className="mt-1">Size: {formatBytes(upload.size_bytes)}</p>
                    <p className="mt-1">Saved status: {upload.status}</p>
                  </div>
                ) : (
                  <div className="mt-4 rounded-lg border border-dashed border-zinc-300 bg-zinc-50 p-4">
                    <p className="text-sm text-zinc-700">Upload will be enabled in the next step</p>
                    <button
                      type="button"
                      disabled
                      className="mt-3 inline-flex min-h-11 items-center rounded-md bg-zinc-200 px-4 text-sm font-medium text-zinc-500"
                    >
                      Upload
                    </button>
                  </div>
                )}
              </Card>
            </li>
          );
        })}
      </ul>
      <div>
        <button
          type="button"
          disabled
          className="inline-flex min-h-11 items-center rounded-md bg-zinc-200 px-4 text-sm font-medium text-zinc-500"
        >
          Run readiness check
        </button>
        <p className="mt-2 text-sm text-zinc-600">Available after you upload your documents</p>
      </div>
    </>
  );
}

export default function ApplicationPage({ params }: { params: Promise<{ id: string }> }) {
  return (
    <PageContainer>
      <Suspense fallback={<LoadingSkeleton label="Loading checklist" />}>
        <Checklist params={params} />
      </Suspense>
    </PageContainer>
  );
}
