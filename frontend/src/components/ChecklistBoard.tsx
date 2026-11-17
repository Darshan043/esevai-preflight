"use client";

// The checklist the citizen sees. Uploads update the progress without reloading the page.

import { useState } from "react";

import { Card } from "@/components/Card";
import { Disclaimer } from "@/components/Disclaimer";
import { UploadSlot } from "@/components/UploadSlot";
import type { PublicUpload, ValidationResult } from "@/lib/types";

export type ChecklistSlot = {
  id: string;
  name: string;
  description: string | null;
  isMandatory: boolean;
  acceptedFormats: string[];
  maxSizeMb: number;
  validity: string | null;
  upload: PublicUpload | null;
};

export function ChecklistBoard({
  applicationId,
  title,
  statusLabel,
  slots,
  results,
}: {
  applicationId: string;
  title: string;
  statusLabel: string;
  slots: ChecklistSlot[];
  results: ValidationResult[];
}) {
  const [uploads, setUploads] = useState<Record<string, PublicUpload | null>>(() => {
    const initial: Record<string, PublicUpload | null> = {};
    for (const slot of slots) {
      initial[slot.id] = slot.upload;
    }
    return initial;
  });
  const uploadedCount = slots.filter((slot) => uploads[slot.id]).length;
  const progress = slots.length === 0 ? 0 : Math.round((uploadedCount / slots.length) * 100);

  return (
    <>
      <header className="page-banner flex flex-col gap-3">
        <p className="text-xs font-semibold tracking-[0.14em] text-royal uppercase">Document checklist</p>
        <h1 className="text-3xl font-semibold tracking-tight text-navy">{title}</h1>
        <p className="inline-flex w-fit rounded-full bg-sky px-3 py-1 text-sm font-medium text-navy">{statusLabel}</p>
        <div>
          <p className="text-sm font-medium text-ink" id="upload-progress-label">
            {uploadedCount} of {slots.length} required documents uploaded
          </p>
          <div
            className="mt-2 h-3 overflow-hidden rounded-full bg-sky"
            role="progressbar"
            aria-labelledby="upload-progress-label"
            aria-valuemin={0}
            aria-valuemax={slots.length}
            aria-valuenow={uploadedCount}
          >
            <div className="h-full bg-royal" style={{ width: `${progress}%` }} />
          </div>
        </div>
      </header>
      <Disclaimer />
      <ul className="flex flex-col gap-4" data-required-count={slots.length}>
        {slots.map((slot, index) => (
          <li key={slot.id}>
            <Card className="service-card">
              <h2 className="text-xl font-semibold text-navy">
                <span className="mr-2 text-sm font-semibold text-royal">{index + 1}.</span>
                {slot.name}
              </h2>
              <p className="mt-2 text-sm font-medium text-ink">{slot.isMandatory ? "Mandatory" : "Optional"}</p>
              {slot.description ? <p className="mt-2 text-muted">Tip: {slot.description}</p> : null}
              <p className="mt-2 text-sm text-ink">Accepted formats: {slot.acceptedFormats.join(", ")}</p>
              <p className="mt-1 text-sm text-ink">Maximum size: {slot.maxSizeMb} MB</p>
              {slot.validity ? <p className="mt-1 text-sm text-ink">{slot.validity}</p> : null}
              <UploadSlot
                applicationId={applicationId}
                document={slot}
                upload={uploads[slot.id] ?? null}
                results={results}
                onChange={(next) => {
                  setUploads((current) => ({ ...current, [slot.id]: next }));
                }}
              />
            </Card>
          </li>
        ))}
      </ul>
      <div>
        <button
          type="button"
          disabled
          className="inline-flex min-h-11 cursor-not-allowed items-center rounded-lg bg-line px-4 text-sm font-semibold text-muted"
        >
          Run readiness check
        </button>
        <p className="mt-2 text-sm text-muted">Available in a later step</p>
      </div>
    </>
  );
}
