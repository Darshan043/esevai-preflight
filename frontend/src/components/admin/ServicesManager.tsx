"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { slugFromName } from "@/lib/admin-defaults";
import { getAccessToken } from "@/lib/access-token";
import { ApiError, deleteAdminService, duplicateAdminService, fetchAdminServices, updateAdminService } from "@/lib/api";
import type { AdminService } from "@/lib/types";

export function ServicesManager() {
  const router = useRouter();
  const [items, setItems] = useState<AdminService[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [duplicateFor, setDuplicateFor] = useState<AdminService | null>(null);
  const [newName, setNewName] = useState("");
  const [newSlug, setNewSlug] = useState("");

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      const token = await getAccessToken();
      if (!token) {
        router.push("/login?next=/admin/services");
        return;
      }
      try {
        const body = await fetchAdminServices(token);
        if (cancelled) {
          return;
        }
        setItems(body.items);
        setError(null);
      } catch (caught: unknown) {
        if (cancelled) {
          return;
        }
        if (caught instanceof ApiError && caught.status === 401) {
          router.push("/login?next=/admin/services");
          return;
        }
        setError(caught instanceof Error ? caught.message : "The services could not be loaded.");
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [attempt, router]);

  async function toggleActive(service: AdminService) {
    const token = await getAccessToken();
    if (!token) {
      return;
    }
    try {
      await updateAdminService(token, service.id, {
        slug: service.slug,
        name_en: service.name_en,
        name_ta: service.name_ta,
        description: service.description,
        is_active: !service.is_active,
        is_verified: service.is_verified,
        confirm_verified: service.is_verified,
      });
      setAttempt((current) => current + 1);
    } catch (caught: unknown) {
      setError(caught instanceof Error ? caught.message : "The service could not be updated.");
    }
  }

  async function remove(service: AdminService) {
    if (!window.confirm(`Delete ${service.name_en}? This cannot be undone.`)) {
      return;
    }
    const token = await getAccessToken();
    if (!token) {
      return;
    }
    try {
      await deleteAdminService(token, service.id);
      setAttempt((current) => current + 1);
    } catch (caught: unknown) {
      setError(caught instanceof Error ? caught.message : "The service could not be deleted.");
    }
  }

  async function duplicate() {
    if (!duplicateFor) {
      return;
    }
    const token = await getAccessToken();
    if (!token) {
      return;
    }
    try {
      const result = await duplicateAdminService(token, duplicateFor.id, { new_slug: newSlug, new_name_en: newName });
      setDuplicateFor(null);
      router.push(`/admin/services/${result.service.id}`);
    } catch (caught: unknown) {
      setError(caught instanceof Error ? caught.message : "The copy could not be created.");
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <header className="page-banner">
        <p className="text-xs font-semibold tracking-[0.14em] text-royal uppercase">Administration</p>
        <h1 className="mt-1 text-3xl font-semibold tracking-tight text-navy">Services</h1>
        <p className="mt-2 text-muted">Create a draft, add documents, then activate it after you have checked the official portal.</p>
        <p className="mt-4">
          <Link href="/admin/services/new" className="btn-primary">
            New service
          </Link>
        </p>
      </header>
      {loading ? <p className="text-muted">Loading services...</p> : null}
      {!loading && error ? (
        <div className="rounded-md border border-red-200 bg-red-50 p-4 text-red-800" role="alert">
          <p>{error}</p>
          <button
            type="button"
            className="btn-primary mt-3"
            onClick={() => {
              setLoading(true);
              setAttempt((current) => current + 1);
            }}
          >
            Retry
          </button>
        </div>
      ) : null}
      {!loading && !error ? (
        <section className="panel overflow-x-auto">
          {items.length === 0 ? (
            <p className="text-muted">No services yet.</p>
          ) : (
            <table className="w-full min-w-[44rem] text-left text-sm">
              <thead>
                <tr className="border-b border-line text-muted">
                  <th className="py-2 pr-3 font-medium">Name</th>
                  <th className="py-2 pr-3 font-medium">Slug</th>
                  <th className="py-2 pr-3 font-medium">Active</th>
                  <th className="py-2 pr-3 font-medium">Status</th>
                  <th className="py-2 pr-3 font-medium">Documents</th>
                  <th className="py-2 pr-3 font-medium">Applications</th>
                  <th className="py-2 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {items.map((service) => {
                  const used = (service.applications ?? 0) > 0;
                  return (
                    <tr key={service.id} className="border-b border-line">
                      <td className="py-2 pr-3">{service.name_en}</td>
                      <td className="py-2 pr-3">{service.slug}</td>
                      <td className="py-2 pr-3">
                        <button type="button" className="btn-secondary" onClick={() => void toggleActive(service)}>
                          {service.is_active ? "On" : "Off"}
                        </button>
                      </td>
                      <td className="py-2 pr-3">
                        {service.is_verified ? (
                          <span className="rounded-full bg-india/15 px-2 py-1 text-india">Verified</span>
                        ) : (
                          <span className="rounded-full bg-saffron/15 px-2 py-1 text-saffron">Draft</span>
                        )}
                      </td>
                      <td className="py-2 pr-3">
                        {service.documents_active ?? 0}/{service.documents_total ?? 0}
                      </td>
                      <td className="py-2 pr-3">{service.applications ?? 0}</td>
                      <td className="py-2">
                        <div className="flex flex-wrap gap-2">
                          <Link href={`/admin/services/${service.id}`} className="btn-secondary">
                            Edit
                          </Link>
                          <button
                            type="button"
                            className="btn-secondary"
                            onClick={() => {
                              setDuplicateFor(service);
                              setNewName(`${service.name_en} (copy)`);
                              setNewSlug(slugFromName(`${service.slug}-copy`));
                            }}
                          >
                            Duplicate
                          </button>
                          {used ? (
                            <span className="self-center text-muted" title="Used – deactivate instead">
                              Used – deactivate instead
                            </span>
                          ) : (
                            <button type="button" className="btn-secondary" onClick={() => void remove(service)}>
                              Delete
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </section>
      ) : null}
      {duplicateFor ? (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-navy/50 p-4" role="dialog" aria-modal="true" aria-labelledby="duplicate-title">
          <form
            className="panel w-full max-w-md"
            onSubmit={(event) => {
              event.preventDefault();
              void duplicate();
            }}
          >
            <h2 id="duplicate-title" className="text-lg font-semibold text-navy">
              Duplicate {duplicateFor.name_en}
            </h2>
            <p className="mt-2 text-sm text-muted">The copy starts inactive and unverified.</p>
            <label className="mt-4 block text-sm font-medium">
              New name
              <input className="field" value={newName} onChange={(event) => setNewName(event.target.value)} required />
            </label>
            <label className="mt-4 block text-sm font-medium">
              New slug
              <input className="field" value={newSlug} onChange={(event) => setNewSlug(event.target.value)} required />
            </label>
            <div className="mt-4 flex gap-2">
              <button type="submit" className="btn-primary">
                Create copy
              </button>
              <button type="button" className="btn-secondary" onClick={() => setDuplicateFor(null)}>
                Cancel
              </button>
            </div>
          </form>
        </div>
      ) : null}
    </div>
  );
}
