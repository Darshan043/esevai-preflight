"use client";

// One checklist slot: choose a file, upload it, then preview, replace, or delete it.

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { StatusBadge } from "@/components/StatusBadge";
import {
  ApiError,
  NETWORK_ERROR,
  deleteUploadedDocument,
  fetchPreviewUrl,
  isPublicUpload,
  uploadUrl,
} from "@/lib/api";
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
  onChange,
}: {
  applicationId: string;
  document: SlotDocument;
  upload: PublicUpload | null;
  results: ValidationResult[];
  onChange: (next: PublicUpload | null) => void;
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
  const shown = upload && upload.id !== removedId ? upload : null;
  const status = slotStatus(shown, results);

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
    setMessage(null);
    setPendingFile(file);
    setProgress(0);
    void send(file);
  }

  async function send(file: File) {
    const token = await accessToken();
    if (!token) {
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
      if (event.lengthComputable) {
        setProgress(Math.round((event.loaded / event.total) * 100));
      }
    };
    xhr.onerror = () => {
      setProgress(null);
      setMessage(NETWORK_ERROR);
    };
    xhr.onabort = () => {
      setProgress(null);
      setMessage("Upload cancelled.");
    };
    xhr.onload = () => {
      setProgress(null);
      requestRef.current = null;
      if (xhr.status === 401) {
        goToLogin();
        return;
      }
      if (xhr.status < 200 || xhr.status >= 300) {
        try {
          const parsed = JSON.parse(xhr.responseText) as { detail?: string };
          setMessage(parsed.detail || `The backend returned status ${xhr.status}.`);
        } catch {
          setMessage(`The backend returned status ${xhr.status}.`);
        }
        return;
      }
      const parsed: unknown = JSON.parse(xhr.responseText);
      if (!isPublicUpload(parsed)) {
        setMessage("The server response could not be read.");
        return;
      }
      onChange(parsed);
      setPendingFile(null);
      setMessage(null);
    };
    xhr.send(body);
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
    try {
      await deleteUploadedDocument(shown.id, token);
      // Hide this file even if the page still has the old checklist props.
      setRemovedId(shown.id);
      onChange(null);
      setConfirmingDelete(false);
      setMessage(null);
      router.refresh();
    } catch (caught) {
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
      <div className="mb-3">
        <StatusBadge status={status} />
      </div>
      {shown ? (
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
              disabled={deleting}
            >
              Replace
            </button>
            <button
              type="button"
              className="btn-secondary border-red-200 text-red-800"
              onClick={() => setConfirmingDelete(true)}
              disabled={deleting}
            >
              Delete
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
      {progress != null ? (
        <div className="mt-3">
          <p className="text-sm text-ink" id={`${document.id}-progress`}>
            Uploading {progress}%
          </p>
          <div
            className="mt-2 h-3 overflow-hidden rounded-full bg-sky"
            role="progressbar"
            aria-labelledby={`${document.id}-progress`}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={progress}
          >
            <div className="h-full bg-royal" style={{ width: `${progress}%` }} />
          </div>
          <button
            type="button"
            className="btn-secondary mt-3"
            onClick={() => requestRef.current?.abort()}
          >
            Cancel
          </button>
        </div>
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
