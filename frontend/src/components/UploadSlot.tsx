"use client";

// One checklist slot: choose a file, upload it, then preview, replace, or delete it.

import { LoaderCircle } from "lucide-react";
import { useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { AiDetailsPanel } from "@/components/AiDetails";
import { CheckList } from "@/components/CheckList";
import { StatusBadge } from "@/components/StatusBadge";
import { extractFailureMessage, visibleAiDetails } from "@/lib/ai";
import {
  ApiError,
  NETWORK_ERROR,
  deleteUploadedDocument,
  extractDocument,
  fetchPreviewUrl,
  isPublicUpload,
  processDocument,
  uploadUrl,
} from "@/lib/api";
import { metricsAfterReadFailure, replacementLabel, showStoredResults, type ReplacementPhase } from "@/lib/replacement";
import { slotStatus } from "@/lib/slot-status";
import { createClient } from "@/lib/supabase/client";
import type { PublicUpload, ValidationResult } from "@/lib/types";

type SlotDocument = {
  id: string;
  name: string;
  description: string | null;
  isMandatory: boolean;
  acceptedFormats: string[];
  maxSizeMb: number;
  validity: string | null;
};

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

function formatWhen(value: string | null): string {
  if (!value) {
    return "Time not recorded";
  }
  return value.replace("T", " ").slice(0, 16);
}

function metricNumber(metrics: Record<string, unknown> | undefined, key: string): number | null {
  const value = metrics?.[key];
  return typeof value === "number" ? value : null;
}

function metricText(value: number | null, digits = 0): string {
  if (value == null) {
    return "Not available";
  }
  return value.toFixed(digits);
}

function QualityPanel({ metrics, text }: { metrics: Record<string, unknown>; text: string | null }) {
  const width = metricNumber(metrics, "width");
  const height = metricNumber(metrics, "height");
  const confidence = metricNumber(metrics, "ocr_mean_confidence");
  const resolution = width != null && height != null ? `${width} x ${height}` : "Not available";
  const rows = [
    ["Sharpness", metricText(metricNumber(metrics, "blur_score"), 1)],
    ["Brightness", metricText(metricNumber(metrics, "brightness_mean"), 0)],
    ["Resolution", resolution],
    ["Tilt", metricNumber(metrics, "skew_angle_degrees") == null ? "Not available" : `${metricText(metricNumber(metrics, "skew_angle_degrees"), 1)} degrees`],
    ["Pages", metricText(metricNumber(metrics, "page_count"), 0)],
    ["OCR confidence", confidence == null ? "Not available" : `${Math.round(confidence)}%`],
  ];

  return (
    <section className="mt-4 rounded-lg border border-line bg-white p-4" aria-label="Quality indicators">
      <h3 className="text-sm font-semibold text-navy">Quality indicators</h3>
      <dl className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
        {rows.map(([label, value]) => (
          <div key={label}>
            <dt className="text-muted">{label}</dt>
            <dd className="font-medium text-ink">{value}</dd>
          </div>
        ))}
      </dl>
      <details className="mt-3">
        <summary className="min-h-11 cursor-pointer text-sm font-medium text-royal">
          Show text read from this document (ID numbers are hidden)
        </summary>
        <pre className="mt-2 max-h-48 overflow-auto whitespace-pre-wrap rounded-md border border-line bg-sky p-3 text-sm text-ink [font-family:ui-monospace,var(--font-tamil),monospace]">
          {text?.trim() ? text : "No text was read."}
        </pre>
      </details>
      <p className="mt-2 text-sm text-muted">These numbers describe the photo. The checks below say what to fix.</p>
    </section>
  );
}

async function accessToken(): Promise<string | null> {
  const supabase = createClient();
  const { data } = await supabase.auth.getSession();
  return data.session?.access_token ?? null;
}

export function UploadSlot({
  applicationId,
  document,
  upload,
  results,
  explanations,
  onChange,
  onActivity,
  onSuspend,
  onUndoSuspend,
}: {
  applicationId: string;
  document: SlotDocument;
  upload: PublicUpload | null;
  results: ValidationResult[];
  explanations?: Record<string, string>;
  onChange: (next: PublicUpload | null) => void;
  onActivity?: () => void | Promise<void>;
  onSuspend?: () => void;
  onUndoSuspend?: () => void;
}) {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement | null>(null);
  const requestRef = useRef<XMLHttpRequest | null>(null);
  const [progress, setProgress] = useState<number | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [pendingFile, setPendingFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [removedId, setRemovedId] = useState<string | null>(null);
  const [reading, setReading] = useState(false);
  const [processError, setProcessError] = useState<string | null>(null);
  const [aiReading, setAiReading] = useState(false);
  const [aiNotice, setAiNotice] = useState<string | null>(null);
  const [phase, setPhase] = useState<ReplacementPhase>("idle");
  const abortRef = useRef<AbortController | null>(null);
  const ignoreRef = useRef(false);
  const beforeRead = useRef<PublicUpload | null>(null);
  const operationRef = useRef(0);
  const shown = upload && upload.id !== removedId ? upload : null;
  const phaseLabel = replacementLabel(phase, progress);
  const showCurrent = showStoredResults(phase);
  const status = !showCurrent || reading ? "Processing" : slotStatus(shown, results);
  const waiting = !showCurrent || reading || shown?.status === "processing";
  const savedError =
    shown?.status === "failed" && typeof shown.quality_metrics?.error === "string" ? shown.quality_metrics.error : null;
  const visibleError = processError || savedError;

  function goToLogin() {
    router.push(`/login?next=/applications/${applicationId}`);
  }

  function checkFile(file: File): string | null {
    const extension = file.name.includes(".") ? file.name.split(".").pop()?.toLowerCase() ?? "" : "";
    const allowed = document.acceptedFormats.map((item) => item.toLowerCase().replace(/^\./, ""));
    if (!["jpg", "jpeg", "png", "pdf"].includes(extension) || !allowed.includes(extension)) {
      return "This file type is not allowed. Use JPG, PNG, or PDF.";
    }
    const limit = document.maxSizeMb * 1024 * 1024;
    if (file.size <= 0) {
      return "This file is empty.";
    }
    if (file.size > limit) {
      return `This file is larger than ${document.maxSizeMb} MB.`;
    }
    return null;
  }

  function nextOperation(): number {
    operationRef.current += 1;
    return operationRef.current;
  }

  function isCurrent(operation: number): boolean {
    return operationRef.current === operation;
  }

  function failUpload(operation: number, text: string) {
    if (!isCurrent(operation)) {
      return;
    }
    setProgress(null);
    setPhase("idle");
    setMessage(text);
    onUndoSuspend?.();
  }

  function startUpload(file: File, replacing: boolean) {
    if (replacing) {
      const confirmed = window.confirm("Replace the current file? The old file will be removed.");
      if (!confirmed) {
        return;
      }
    }
    const problem = checkFile(file);
    if (problem) {
      setMessage(problem);
      setPendingFile(file);
      return;
    }
    const operation = nextOperation();
    ignoreRef.current = true;
    abortRef.current?.abort();
    requestRef.current?.abort();
    onSuspend?.();
    setMessage(null);
    setProcessError(null);
    setPendingFile(file);
    setProgress(0);
    setPhase("uploading");
    void send(file, operation);
  }

  async function send(file: File, operation: number) {
    const token = await accessToken();
    if (!isCurrent(operation)) {
      return;
    }
    if (!token) {
      failUpload(operation, "Please sign in again.");
      goToLogin();
      return;
    }
    const body = new FormData();
    body.append("file", file);
    const xhr = new XMLHttpRequest();
    requestRef.current = xhr;
    xhr.open("POST", uploadUrl(applicationId, document.id));
    xhr.setRequestHeader("Authorization", `Bearer ${token}`);
    xhr.upload.onprogress = (event) => {
      if (!isCurrent(operation) || !event.lengthComputable) {
        return;
      }
      setProgress(Math.round((event.loaded / event.total) * 100));
    };
    xhr.onerror = () => {
      requestRef.current = null;
      failUpload(operation, NETWORK_ERROR);
    };
    xhr.onabort = () => {
      if (requestRef.current === xhr) {
        requestRef.current = null;
      }
      failUpload(operation, "Upload cancelled.");
    };
    xhr.onload = () => {
      if (requestRef.current === xhr) {
        requestRef.current = null;
      }
      if (!isCurrent(operation)) {
        return;
      }
      setProgress(null);
      if (xhr.status === 401) {
        failUpload(operation, "Please sign in again.");
        goToLogin();
        return;
      }
      if (xhr.status < 200 || xhr.status >= 300) {
        try {
          const parsed = JSON.parse(xhr.responseText) as { detail?: string };
          failUpload(operation, parsed.detail || `The backend returned status ${xhr.status}.`);
        } catch {
          failUpload(operation, `The backend returned status ${xhr.status}.`);
        }
        return;
      }
      let parsed: unknown;
      try {
        parsed = JSON.parse(xhr.responseText);
      } catch {
        failUpload(operation, "The server response could not be read.");
        return;
      }
      if (!isPublicUpload(parsed)) {
        failUpload(operation, "The server response could not be read.");
        return;
      }
      setPhase("uploaded");
      onChange(parsed);
      setPendingFile(null);
      setMessage(null);
      void readDocument(parsed, operation);
    };
    xhr.send(body);
  }

  function startRead(current: PublicUpload) {
    const operation = nextOperation();
    ignoreRef.current = true;
    abortRef.current?.abort();
    onSuspend?.();
    void readDocument(current, operation);
  }

  async function readAiDetails(current: PublicUpload, token: string, operation: number, force = false) {
    setAiReading(true);
    setAiNotice(null);
    try {
      const fields = await extractDocument(current.id, token, force);
      if (!isCurrent(operation)) {
        return;
      }
      onChange({ ...current, extracted_fields: fields });
    } catch (caught) {
      if (!isCurrent(operation)) {
        return;
      }
      setAiNotice(
        caught instanceof ApiError
          ? extractFailureMessage(caught.status, caught.message)
          : "AI assistance is unavailable right now – your standard checks still work",
      );
    } finally {
      if (isCurrent(operation)) {
        setAiReading(false);
      }
    }
  }

  async function readDocument(current: PublicUpload, operation: number) {
    const token = await accessToken();
    if (!isCurrent(operation)) {
      return;
    }
    if (!token) {
      setPhase("idle");
      goToLogin();
      return;
    }
    ignoreRef.current = false;
    beforeRead.current = current;
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setReading(true);
    setProcessError(null);
    setMessage(null);
    setPhase("reading");
    setAiNotice(null);
    onChange({ ...current, status: "processing", quality_metrics: {}, ocr_text_masked: null, extracted_fields: {} });
    try {
      const result = await processDocument(current.id, token, controller.signal);
      if (!isCurrent(operation) || ignoreRef.current) {
        return;
      }
      const readUpload: PublicUpload = {
        ...current,
        status: result.status,
        updated_at: result.updated_at || current.updated_at,
        quality_metrics: result.quality_metrics ?? {},
        ocr_text_masked: result.ocr_text_masked,
        extracted_fields: {},
      };
      onChange(readUpload);
      setProcessError(null);
      if (result.status === "processed") {
        await readAiDetails(readUpload, token, operation);
      }
      if (!isCurrent(operation)) {
        return;
      }
      setPhase("checking");
      await onActivity?.();
      if (!isCurrent(operation)) {
        return;
      }
      setPhase("idle");
    } catch (caught) {
      if (!isCurrent(operation) || ignoreRef.current || (caught instanceof DOMException && caught.name === "AbortError")) {
        return;
      }
      if (caught instanceof ApiError && caught.status === 401) {
        setPhase("idle");
        goToLogin();
        return;
      }
      const body = caught instanceof ApiError ? caught.body : null;
      const failedStatus = body && typeof body.status === "string" ? body.status : "";
      const failedReading = metricsAfterReadFailure(body);
      if (failedStatus === "uploaded" || failedStatus === "processing" || failedStatus === "processed" || failedStatus === "failed") {
        onChange({
          ...current,
          status: failedStatus,
          updated_at: typeof body?.updated_at === "string" ? body.updated_at : current.updated_at,
          quality_metrics: failedReading.quality_metrics,
          ocr_text_masked: failedReading.ocr_text_masked,
        });
      } else {
        onChange({ ...current, status: "failed", quality_metrics: {}, ocr_text_masked: null });
      }
      setProcessError(caught instanceof Error ? caught.message : NETWORK_ERROR);
      setPhase("checking");
      try {
        await onActivity?.();
      } catch {
        // The checklist shows its own error. This slot must not stay on the old results.
      }
      if (isCurrent(operation)) {
        setPhase("idle");
      }
    } finally {
      if (abortRef.current === controller) {
        setReading(false);
      }
    }
  }

  function ignoreReading() {
    ignoreRef.current = true;
    abortRef.current?.abort();
    setReading(false);
    setPhase("idle");
    if (beforeRead.current) {
      onChange(beforeRead.current);
    }
  }

  async function preview() {
    if (!shown) {
      return;
    }
    const token = await accessToken();
    if (!token) {
      goToLogin();
      return;
    }
    try {
      const link = await fetchPreviewUrl(shown.id, token);
      if (link.mime_type === "application/pdf" || shown.mime_type === "application/pdf") {
        window.open(link.url, "_blank", "noopener,noreferrer");
        return;
      }
      setPreviewUrl(link.url);
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 401) {
        goToLogin();
        return;
      }
      setMessage(caught instanceof Error ? caught.message : NETWORK_ERROR);
    }
  }

  async function remove() {
    if (!shown) {
      return;
    }
    const token = await accessToken();
    if (!token) {
      goToLogin();
      return;
    }
    setDeleting(true);
    setMessage(null);
    onSuspend?.();
    try {
      await deleteUploadedDocument(shown.id, token);
      // Hide this file even if the page still has the old checklist props.
      setRemovedId(shown.id);
      onChange(null);
      setConfirmingDelete(false);
      setMessage(null);
      await onActivity?.();
      router.refresh();
    } catch (caught) {
      onUndoSuspend?.();
      if (caught instanceof ApiError && caught.status === 401) {
        goToLogin();
        return;
      }
      setMessage(caught instanceof Error ? caught.message : NETWORK_ERROR);
    } finally {
      setDeleting(false);
    }
  }

  return (
    <div className="mt-4">
      <div className="mb-3" aria-live="polite">
        {showCurrent ? <StatusBadge status={status} /> : null}
        {aiReading ? (
          <p className="flex items-center gap-2 text-sm text-ink" role="status">
            <LoaderCircle aria-hidden="true" className="h-4 w-4 animate-spin text-royal" />
            AI is reading the details…
          </p>
        ) : null}
        {phaseLabel ? (
          <p className="flex items-center gap-2 text-sm text-ink" role="status">
            <LoaderCircle aria-hidden="true" className="h-4 w-4 animate-spin text-royal" />
            {phaseLabel}
          </p>
        ) : null}
      </div>
      {phase === "uploading" ? (
        <p className="mb-3 text-sm text-ink">New file: {pendingFile?.name ?? "Selected file"}</p>
      ) : shown ? (
        <div className="rounded-lg border border-line bg-sky p-4 text-sm text-ink">
          <p>File: {shown.original_filename ?? "Uploaded file"}</p>
          <p className="mt-1">Size: {formatBytes(shown.size_bytes)}</p>
          <p className="mt-1">Uploaded: {formatWhen(shown.created_at)}</p>
          <div className="mt-3 flex flex-wrap gap-2">
            <button type="button" className="btn-primary" onClick={() => void preview()} aria-label={`Preview ${document.name}`}>
              Preview
            </button>
            <button
              type="button"
              className="btn-secondary"
              onClick={() => inputRef.current?.click()}
              aria-label={`Replace ${document.name}`}
              disabled={deleting || waiting}
            >
              Replace
            </button>
            <button
              type="button"
              className="btn-secondary border-red-200 text-red-800"
              onClick={() => setConfirmingDelete(true)}
              disabled={deleting || waiting}
            >
              Delete
            </button>
            <button
              type="button"
              className="btn-secondary"
              onClick={() => startRead(shown)}
              disabled={waiting}
            >
              Re-read document
            </button>
          </div>
          {confirmingDelete ? (
            <div className="mt-3 rounded-lg border border-red-200 bg-white p-3" role="dialog" aria-label="Confirm delete">
              <p>Delete this file? This cannot be undone.</p>
              <div className="mt-3 flex flex-wrap gap-2">
                <button type="button" className="btn-primary" onClick={() => void remove()} disabled={deleting}>
                  {deleting ? "Deleting..." : "Delete file"}
                </button>
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => setConfirmingDelete(false)}
                  disabled={deleting}
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : null}
        </div>
      ) : (
        <div
          className={`rounded-lg border border-dashed p-4 ${dragOver ? "border-royal bg-white" : "border-royal/40 bg-sky/60"}`}
          onDragOver={(event) => {
            event.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(event) => {
            event.preventDefault();
            setDragOver(false);
            const file = event.dataTransfer.files[0];
            if (file) {
              startUpload(file, false);
            }
          }}
        >
          <p className="text-sm font-medium text-navy">Choose a JPG, PNG, or PDF, or drop it here.</p>
          <button
            type="button"
            className="btn-primary mt-3"
            onClick={() => inputRef.current?.click()}
            aria-label={`Upload ${document.name}`}
          >
            Choose file
          </button>
        </div>
      )}
      <input
        ref={inputRef}
        type="file"
        accept=".jpg,.jpeg,.png,.pdf,image/*"
        className="sr-only"
        aria-label={`File for ${document.name}`}
        onChange={(event) => {
          const file = event.target.files?.[0];
          event.target.value = "";
          if (file) {
            startUpload(file, Boolean(shown));
          }
        }}
      />
      {phase === "uploading" ? (
        <div className="mt-3">
          {progress != null && progress > 0 ? (
            <>
              <p className="sr-only" id={`${document.id}-progress`}>
                Uploading {progress}%
              </p>
              <div
                className="h-3 overflow-hidden rounded-full bg-sky"
                role="progressbar"
                aria-labelledby={`${document.id}-progress`}
                aria-valuemin={0}
                aria-valuemax={100}
                aria-valuenow={progress}
              >
                <div className="h-full bg-royal" style={{ width: `${progress}%` }} />
              </div>
            </>
          ) : null}
          <button
            type="button"
            className="btn-secondary mt-3"
            onClick={() => {
              if (requestRef.current) {
                requestRef.current.abort();
                return;
              }
              failUpload(operationRef.current, "Upload cancelled.");
            }}
          >
            Cancel
          </button>
        </div>
      ) : null}
      {phase === "reading" && reading ? (
        <button type="button" className="btn-secondary mt-3" onClick={ignoreReading}>
          Cancel
        </button>
      ) : null}
      {message ? (
        <div className="mt-3" role="alert">
          <p className="text-sm text-red-800">{message}</p>
          {pendingFile ? (
            <button type="button" className="btn-secondary mt-2" onClick={() => startUpload(pendingFile, Boolean(shown))}>
              Retry
            </button>
          ) : null}
        </div>
      ) : null}
      {visibleError ? (
        <div className="mt-3" role="alert">
          <p className="text-sm text-red-800">{visibleError}</p>
          {shown ? (
            <button type="button" className="btn-secondary mt-2" onClick={() => startRead(shown)} disabled={waiting}>
              Try again
            </button>
          ) : null}
        </div>
      ) : null}
      {shown && shown.status === "processed" && (showCurrent || phase === "checking") ? (
        <QualityPanel metrics={shown.quality_metrics ?? {}} text={shown.ocr_text_masked ?? null} />
      ) : null}
      {aiNotice ? (
        <div className="mt-3" role="status">
          <p className="text-sm text-ink">{aiNotice}</p>
          {shown ? (
            <button
              type="button"
              className="btn-secondary mt-2"
              onClick={() => {
                void (async () => {
                  const token = await accessToken();
                  if (!token || !shown) {
                    return;
                  }
                  await readAiDetails(shown, token, operationRef.current, true);
                })();
              }}
            >
              Try AI again
            </button>
          ) : null}
        </div>
      ) : null}
      {showCurrent && shown
        ? (() => {
            const details = visibleAiDetails(shown.extracted_fields);
            return details ? <AiDetailsPanel details={details} /> : null;
          })()
        : null}
      {showCurrent && shown ? (
        <CheckList
          results={results.filter((result) => result.uploaded_document_id === shown.id)}
          explanations={explanations}
        />
      ) : null}
      {previewUrl ? (
        <div className="fixed inset-0 z-50 grid place-items-center bg-navy/70 p-4" role="dialog" aria-modal="true" aria-label="Document preview">
          <div className="max-h-[90vh] w-full max-w-3xl overflow-auto rounded-lg bg-white p-4">
            {/* The signed address is used once for this open preview and then forgotten. */}
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={previewUrl} alt={shown?.original_filename ?? document.name} className="mx-auto max-h-[70vh] w-auto" />
            <button
              type="button"
              className="btn-primary mt-4"
              onClick={() => setPreviewUrl(null)}
            >
              Close
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
