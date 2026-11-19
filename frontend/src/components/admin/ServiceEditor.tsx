"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState, type FormEvent } from "react";

import { DocumentForm } from "@/components/admin/DocumentForm";
import { emptyDocument, emptyService, pickRules, photoPreset } from "@/lib/admin-defaults";
import { getAccessToken } from "@/lib/access-token";
import {
  ApiError,
  createAdminDocument,
  createAdminService,
  deleteAdminDocument,
  fetchAdminService,
  reorderAdminDocuments,
  updateAdminDocument,
  updateAdminService,
} from "@/lib/api";
import type { AdminDocument, AdminDocumentInput, AdminFieldError, AdminService, AdminServiceInput } from "@/lib/types";

export function ServiceEditor({ serviceId }: { serviceId?: string }) {
  const router = useRouter();
  const [service, setService] = useState<AdminServiceInput>(emptyService());
  const [saved, setSaved] = useState<AdminService | null>(null);
  const [documents, setDocuments] = useState<AdminDocument[]>([]);
  const [loading, setLoading] = useState(Boolean(serviceId));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<AdminFieldError[]>([]);
  const [confirmVerified, setConfirmVerified] = useState(false);
  const [editing, setEditing] = useState<AdminDocument | "new" | null>(null);
  const [docErrors, setDocErrors] = useState<AdminFieldError[]>([]);
  const snapshot = useMemo(() => JSON.stringify(service), [service]);
  const [clean, setClean] = useState(snapshot);
  const dirty = snapshot !== clean;

  useEffect(() => {
    if (!serviceId) {
      return;
    }
    void (async () => {
      const token = await getAccessToken();
      if (!token) {
        router.push("/login?next=/admin");
        return;
      }
      try {
        const detail = await fetchAdminService(token, serviceId);
        const next: AdminServiceInput = {
          slug: detail.service.slug,
          name_en: detail.service.name_en,
          name_ta: detail.service.name_ta ?? "",
          description: detail.service.description ?? "",
          is_active: detail.service.is_active,
          is_verified: detail.service.is_verified,
          confirm_verified: detail.service.is_verified,
        };
        setSaved(detail.service);
        setService(next);
        setClean(JSON.stringify(next));
        setDocuments(detail.documents);
      } catch (caught: unknown) {
        if (caught instanceof ApiError && caught.status === 401) {
          router.push("/login?next=/admin");
          return;
        }
        setError(caught instanceof Error ? caught.message : "The service could not be loaded.");
      } finally {
        setLoading(false);
      }
    })();
  }, [router, serviceId]);

  useEffect(() => {
    function warn(event: BeforeUnloadEvent) {
      if (dirty) {
        event.preventDefault();
      }
    }
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [dirty]);

  async function saveService(event: FormEvent) {
    event.preventDefault();
    if (busy) {
      return;
    }
    setBusy(true);
    setError(null);
    setFieldErrors([]);
    const token = await getAccessToken();
    if (!token) {
      router.push("/login?next=/admin");
      return;
    }
    const payload: AdminServiceInput = {
      ...service,
      confirm_verified: service.is_verified ? confirmVerified || service.confirm_verified === true : false,
    };
    if (service.is_verified && !payload.confirm_verified) {
      setConfirmVerified(false);
      setError("Tick the confirmation before marking this service as Verified.");
      setBusy(false);
      return;
    }
    try {
      const result = serviceId ? await updateAdminService(token, serviceId, payload) : await createAdminService(token, payload);
      setSaved(result);
      setClean(JSON.stringify(service));
      if (!serviceId) {
        router.push(`/admin/services/${result.id}`);
      }
    } catch (caught: unknown) {
      if (caught instanceof ApiError) {
        setFieldErrors(caught.fieldErrors);
        setError(caught.message);
      } else {
        setError("The service could not be saved.");
      }
    } finally {
      setBusy(false);
    }
  }

  async function saveDocument(payload: AdminDocumentInput) {
    const id = saved?.id || serviceId;
    if (!id) {
      setError("Save the service first, then add documents.");
      return;
    }
    setBusy(true);
    setDocErrors([]);
    const token = await getAccessToken();
    if (!token) {
      router.push("/login?next=/admin");
      return;
    }
    try {
      if (editing && editing !== "new") {
        await updateAdminDocument(token, editing.id, payload);
      } else {
        await createAdminDocument(token, id, payload);
      }
      const detail = await fetchAdminService(token, id);
      setDocuments(detail.documents);
      setEditing(null);
    } catch (caught: unknown) {
      if (caught instanceof ApiError) {
        setDocErrors(caught.fieldErrors);
        setError(caught.message);
      } else {
        setError("The document could not be saved.");
      }
    } finally {
      setBusy(false);
    }
  }

  async function move(index: number, direction: -1 | 1) {
    const id = saved?.id || serviceId;
    if (!id) {
      return;
    }
    const next = [...documents];
    const target = index + direction;
    if (target < 0 || target >= next.length) {
      return;
    }
    const swap = next[index];
    next[index] = next[target];
    next[target] = swap;
    const token = await getAccessToken();
    if (!token) {
      return;
    }
    try {
      await reorderAdminDocuments(token, id, next.map((item) => item.id));
      const detail = await fetchAdminService(token, id);
      setDocuments(detail.documents);
    } catch (caught: unknown) {
      setError(caught instanceof Error ? caught.message : "The order could not be saved.");
    }
  }

  async function toggleDocument(document: AdminDocument) {
    const token = await getAccessToken();
    if (!token) {
      return;
    }
    try {
      await updateAdminDocument(token, document.id, toInput(document, { is_active: !document.is_active }));
      const id = saved?.id || serviceId;
      if (id) {
        setDocuments((await fetchAdminService(token, id)).documents);
      }
    } catch (caught: unknown) {
      setError(caught instanceof Error ? caught.message : "The document could not be updated.");
    }
  }

  async function removeDocument(document: AdminDocument) {
    if (!window.confirm(`Delete ${document.name_en}? This is only allowed when no files have been uploaded.`)) {
      return;
    }
    const token = await getAccessToken();
    if (!token) {
      return;
    }
    try {
      await deleteAdminDocument(token, document.id);
      setDocuments((current) => current.filter((item) => item.id !== document.id));
    } catch (caught: unknown) {
      setError(caught instanceof Error ? caught.message : "The document could not be deleted.");
    }
  }

  if (loading) {
    return <p className="text-muted">Loading service...</p>;
  }

  const currentId = saved?.id || serviceId;
  const applications = saved?.applications ?? 0;
  const slugLocked = applications > 0;

  return (
    <div className="flex flex-col gap-6">
      <header className="page-banner">
        <p className="text-xs font-semibold tracking-[0.14em] text-royal uppercase">Administration</p>
        <h1 className="mt-1 text-3xl font-semibold tracking-tight text-navy">{serviceId ? "Edit service" : "New service"}</h1>
        <p className="mt-2 text-muted">Invalid rules cannot be saved. Citizens only see this service after you mark it Active.</p>
        {currentId && service.slug ? (
          <p className="mt-3">
            <Link href={`/services/${service.slug}`} className="text-royal underline">
              Open citizen view
            </Link>
          </p>
        ) : null}
      </header>
      {error ? (
        <p className="rounded-md border border-red-200 bg-red-50 p-4 text-red-800" role="alert">
          {error}
        </p>
      ) : null}
      {dirty ? <p className="text-sm text-saffron">You have unsaved service changes.</p> : null}
      <form className="panel flex flex-col gap-4" onSubmit={saveService}>
        <label className="text-sm font-medium text-navy">
          English name
          <input className="field" value={service.name_en} onChange={(event) => setService((current) => ({ ...current, name_en: event.target.value }))} required />
        </label>
        <label className="text-sm font-medium text-navy">
          Tamil name
          <input className="field" value={service.name_ta ?? ""} onChange={(event) => setService((current) => ({ ...current, name_ta: event.target.value }))} />
        </label>
        <label className="text-sm font-medium text-navy">
          Slug
          <span className="block font-normal text-muted">Lowercase letters, digits, and hyphens. Locked after the first application.</span>
          <input className="field" value={service.slug} disabled={slugLocked} onChange={(event) => setService((current) => ({ ...current, slug: event.target.value }))} required />
          {slugLocked ? <span className="mt-1 block font-normal text-saffron">Slug is locked because applications exist.</span> : null}
        </label>
        <label className="text-sm font-medium text-navy">
          Description
          <textarea className="field min-h-24" value={service.description ?? ""} onChange={(event) => setService((current) => ({ ...current, description: event.target.value }))} />
        </label>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={service.is_active} onChange={(event) => setService((current) => ({ ...current, is_active: event.target.checked }))} />
          Active (visible to citizens)
        </label>
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={service.is_verified}
            onChange={(event) => {
              if (event.target.checked) {
                const ok = window.confirm("I have checked this document list against the official e-Sevai portal");
                setService((current) => ({ ...current, is_verified: ok, confirm_verified: ok }));
                setConfirmVerified(ok);
                return;
              }
              setService((current) => ({ ...current, is_verified: false, confirm_verified: false }));
              setConfirmVerified(false);
            }}
          />
          Verified
        </label>
        {fieldErrors.map((item) => (
          <p key={`${item.field}-${item.message}`} className="text-sm text-red-700">
            {item.field}: {item.message}
          </p>
        ))}
        <button type="submit" className="btn-primary self-start" disabled={busy}>
          {busy ? "Saving..." : "Save service"}
        </button>
      </form>
      <section className="panel">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-lg font-semibold text-navy">Required documents</h2>
          <button
            type="button"
            className="btn-primary"
            onClick={() => {
              setDocErrors([]);
              setEditing("new");
            }}
            disabled={!currentId}
          >
            Add document
          </button>
        </div>
        {!currentId ? <p className="mt-3 text-sm text-muted">Save the service first, then add the checklist.</p> : null}
        <ol className="mt-4 flex flex-col gap-3">
          {documents.map((document, index) => (
            <li key={document.id} className="rounded-lg border border-line p-3">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div>
                  <p className="font-semibold text-navy">
                    {index + 1}. {document.name_en}{" "}
                    <span className="text-sm font-normal text-muted">{document.code}</span>
                  </p>
                  <p className="mt-1 flex flex-wrap gap-2 text-sm">
                    {document.is_mandatory ? <span className="rounded-full bg-sky px-2 py-0.5">Mandatory</span> : <span className="rounded-full bg-paper px-2 py-0.5">Optional</span>}
                    {document.is_active ? <span>Active</span> : <span className="text-saffron">Inactive</span>}
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <button type="button" className="btn-secondary" onClick={() => move(index, -1)} disabled={index === 0}>
                    Up
                  </button>
                  <button type="button" className="btn-secondary" onClick={() => move(index, 1)} disabled={index === documents.length - 1}>
                    Down
                  </button>
                  <button type="button" className="btn-secondary" onClick={() => void toggleDocument(document)}>
                    {document.is_active ? "Deactivate" : "Activate"}
                  </button>
                  <button type="button" className="btn-secondary" onClick={() => setEditing(document)}>
                    Edit
                  </button>
                  {document.uploads ? (
                    <span className="self-center text-sm text-muted" title="Documents have been uploaded for this item – deactivate it instead">
                      Used – deactivate instead
                    </span>
                  ) : (
                    <button type="button" className="btn-secondary" onClick={() => void removeDocument(document)}>
                      Delete
                    </button>
                  )}
                </div>
              </div>
            </li>
          ))}
        </ol>
      </section>
      {editing ? (
        <DocumentForm
          key={editing === "new" ? "new" : editing.id}
          initial={editing === "new" ? (documents.length === 0 ? photoPreset(10) : emptyDocument((documents.length + 1) * 10)) : toInput(editing)}
          lockedCode={editing !== "new" && Boolean(editing.code_locked || editing.uploads)}
          serverErrors={docErrors}
          busy={busy}
          onSave={saveDocument}
          onCancel={() => setEditing(null)}
        />
      ) : null}
    </div>
  );
}

function toInput(document: AdminDocument, patch: Partial<AdminDocumentInput> = {}): AdminDocumentInput {
  return {
    code: document.code,
    name_en: document.name_en,
    name_ta: document.name_ta,
    description: document.description,
    is_mandatory: document.is_mandatory,
    accepted_formats: document.accepted_formats,
    max_size_mb: document.max_size_mb,
    validity_days: document.validity_days,
    keywords: { en: document.keywords.en ?? [], ta: document.keywords.ta ?? [] },
    required_fields: Array.isArray(document.required_fields) ? document.required_fields.map(String) : [],
    rules: pickRules(document.rules),
    sort_order: document.sort_order,
    is_active: document.is_active,
    ...patch,
  };
}
