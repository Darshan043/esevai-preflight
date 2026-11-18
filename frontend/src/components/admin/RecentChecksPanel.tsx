"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { ApiError, fetchAdminChecks } from "@/lib/api";
import { getAccessToken } from "@/lib/access-token";
import { STATS_FOOTNOTE } from "@/lib/admin-defaults";
import type { AdminChecksPage } from "@/lib/types";

function labelCopy(label: string | null): string {
  if (label === "ready") {
    return "Ready";
  }
  if (label === "almost_ready") {
    return "Almost ready";
  }
  if (label === "not_ready") {
    return "Not ready";
  }
  return "—";
}

export function RecentChecksPanel() {
  const router = useRouter();
  const [page, setPage] = useState(1);
  const [data, setData] = useState<AdminChecksPage | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      const token = await getAccessToken();
      if (!token) {
        router.push("/login?next=/admin/checks");
        return;
      }
      try {
        const body = await fetchAdminChecks(token, page, 20);
        if (cancelled) {
          return;
        }
        setData(body);
        setError(null);
      } catch (caught: unknown) {
        if (cancelled) {
          return;
        }
        if (caught instanceof ApiError && caught.status === 401) {
          router.push("/login?next=/admin/checks");
          return;
        }
        setError(caught instanceof Error ? caught.message : "The recent checks could not be loaded.");
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [page, attempt, router]);

  const totalPages = data ? Math.max(1, Math.ceil(data.total / data.page_size)) : 1;

  return (
    <div className="flex flex-col gap-6">
      <header className="page-banner">
        <p className="text-xs font-semibold tracking-[0.14em] text-royal uppercase">Administration</p>
        <h1 className="mt-1 text-3xl font-semibold tracking-tight text-navy">Recent checks</h1>
        <p className="mt-2 text-muted">Users are shown as anonymous labels such as User #a1b2c3. Document content is never listed.</p>
      </header>
      {loading ? <p className="text-muted">Loading recent checks...</p> : null}
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
      {!loading && !error && data ? (
        <section className="panel overflow-x-auto">
          {data.items.length === 0 ? (
            <p className="text-muted">No applications yet.</p>
          ) : (
            <table className="w-full min-w-[40rem] text-left text-sm">
              <thead>
                <tr className="border-b border-line text-muted">
                  <th className="py-2 pr-3 font-medium">Service</th>
                  <th className="py-2 pr-3 font-medium">User</th>
                  <th className="py-2 pr-3 font-medium">Label</th>
                  <th className="py-2 pr-3 font-medium">Score</th>
                  <th className="py-2 pr-3 font-medium">Documents</th>
                  <th className="py-2 font-medium">Created</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((row) => (
                  <tr key={row.id} className="border-b border-line">
                    <td className="py-2 pr-3">{row.service_name}</td>
                    <td className="py-2 pr-3">{row.user_label}</td>
                    <td className="py-2 pr-3">{labelCopy(row.label)}</td>
                    <td className="py-2 pr-3">{row.score == null ? "—" : row.score}</td>
                    <td className="py-2 pr-3">{row.document_count}</td>
                    <td className="py-2">{row.created_at ? row.created_at.slice(0, 10) : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          <div className="mt-4 flex flex-wrap items-center gap-2">
            <button
              type="button"
              className="btn-secondary"
              disabled={page <= 1}
              onClick={() => {
                setLoading(true);
                setPage((current) => current - 1);
              }}
            >
              Previous
            </button>
            <p className="text-sm text-muted">
              Page {page} of {totalPages}
            </p>
            <button
              type="button"
              className="btn-secondary"
              disabled={page >= totalPages}
              onClick={() => {
                setLoading(true);
                setPage((current) => current + 1);
              }}
            >
              Next
            </button>
          </div>
          <p className="mt-4 text-sm text-muted">{data.footnote || STATS_FOOTNOTE}</p>
        </section>
      ) : null}
    </div>
  );
}
