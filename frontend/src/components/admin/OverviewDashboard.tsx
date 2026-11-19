"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { ApiError, fetchAdminStats, runAdminCleanup, type CleanupSummary } from "@/lib/api";
import { getAccessToken } from "@/lib/access-token";
import { STATS_FOOTNOTE } from "@/lib/admin-defaults";
import type { AdminStats } from "@/lib/types";

const DAY_OPTIONS = [7, 14, 30, 90];

function labelCopy(label: string): string {
  if (label === "ready") {
    return "Ready";
  }
  if (label === "almost_ready") {
    return "Almost ready";
  }
  return "Not ready";
}

export function OverviewDashboard() {
  const router = useRouter();
  const [days, setDays] = useState(14);
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      const token = await getAccessToken();
      if (!token) {
        router.push("/login?next=/admin");
        return;
      }
      try {
        const body = await fetchAdminStats(token, days);
        if (cancelled) {
          return;
        }
        setStats(body);
        setError(null);
      } catch (caught: unknown) {
        if (cancelled) {
          return;
        }
        if (caught instanceof ApiError && caught.status === 401) {
          router.push("/login?next=/admin");
          return;
        }
        if (caught instanceof ApiError && caught.status === 403) {
          setError("Access denied.");
          return;
        }
        setError(caught instanceof Error ? caught.message : "The statistics could not be loaded.");
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [days, attempt, router]);

  const distribution = stats?.score.distribution;
  const totalLabels = (distribution?.ready ?? 0) + (distribution?.almost_ready ?? 0) + (distribution?.not_ready ?? 0);
  const maxActivity = Math.max(1, ...(stats?.activity.map((item) => item.count) ?? [1]));

  return (
    <div className="flex flex-col gap-6">
      <header className="page-banner">
        <p className="text-xs font-semibold tracking-[0.14em] text-royal uppercase">Administration</p>
        <h1 className="mt-1 text-3xl font-semibold tracking-tight text-navy">Overview</h1>
        <p className="mt-2 text-muted">Aggregate usage only. Document files, OCR text, and personal details are never shown here.</p>
      </header>
      <div className="flex flex-wrap items-center gap-2">
        <p className="text-sm font-medium text-navy">Day range</p>
        {DAY_OPTIONS.map((option) => (
          <button
            key={option}
            type="button"
            className={option === days ? "btn-primary" : "btn-secondary"}
            onClick={() => {
              setLoading(true);
              setDays(option);
            }}
            aria-pressed={option === days}
          >
            {option} days
          </button>
        ))}
      </div>
      {loading ? <p className="text-muted">Loading statistics...</p> : null}
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
      {!loading && !error && stats ? (
        <>
          <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard label="Users" value={String(stats.totals.users)} hint={`${stats.totals.admins} admin, ${stats.totals.citizens} citizen`} />
            <StatCard label="Applications" value={String(stats.totals.applications)} hint={`${stats.totals.applications_checked} with a report`} />
            <StatCard label="Reports generated" value={String(stats.totals.applications_checked)} hint={`${stats.totals.documents_processed} documents processed`} />
            <StatCard label="Average score" value={stats.score.average == null ? "—" : stats.score.average.toFixed(1)} hint="Checked applications only" />
          </section>
          <section className="panel">
            <h2 className="text-lg font-semibold text-navy">Readiness labels</h2>
            {totalLabels === 0 ? (
              <p className="mt-3 text-muted">No reports yet.</p>
            ) : (
              <div className="mt-4 flex h-8 overflow-hidden rounded-md" role="img" aria-label="Ready, almost ready, and not ready counts">
                <BarSlice label="Ready" count={distribution?.ready ?? 0} total={totalLabels} className="bg-india" />
                <BarSlice label="Almost ready" count={distribution?.almost_ready ?? 0} total={totalLabels} className="bg-saffron" />
                <BarSlice label="Not ready" count={distribution?.not_ready ?? 0} total={totalLabels} className="bg-red-700" />
              </div>
            )}
            <ul className="mt-3 flex flex-wrap gap-4 text-sm">
              <li>Ready: {distribution?.ready ?? 0}</li>
              <li>Almost ready: {distribution?.almost_ready ?? 0}</li>
              <li>Not ready: {distribution?.not_ready ?? 0}</li>
            </ul>
          </section>
          <section className="panel">
            <h2 className="text-lg font-semibold text-navy">Top reasons documents fail</h2>
            {stats.top_failure_reasons.length === 0 ? (
              <p className="mt-3 text-muted">No failed or warning checks in the current data.</p>
            ) : (
              <ol className="mt-3 flex flex-col gap-2">
                {stats.top_failure_reasons.map((item) => (
                  <li key={`${item.check_code}-${item.status}`} className="flex flex-wrap justify-between gap-2 border-b border-line py-2">
                    <span>
                      {item.check_name || item.check_code}{" "}
                      <span className="text-sm text-muted">({item.status})</span>
                    </span>
                    <span className="font-semibold">{item.count}</span>
                  </li>
                ))}
              </ol>
            )}
          </section>
          <section className="panel overflow-x-auto">
            <h2 className="text-lg font-semibold text-navy">Per service</h2>
            {stats.per_service.length === 0 ? (
              <p className="mt-3 text-muted">No services yet.</p>
            ) : (
              <table className="mt-3 w-full min-w-[32rem] text-left text-sm">
                <thead>
                  <tr className="border-b border-line text-muted">
                    <th className="py-2 pr-3 font-medium">Service</th>
                    <th className="py-2 pr-3 font-medium">Applications</th>
                    <th className="py-2 pr-3 font-medium">Checked</th>
                    <th className="py-2 font-medium">Average score</th>
                  </tr>
                </thead>
                <tbody>
                  {stats.per_service.map((row) => (
                    <tr key={row.service_id} className="border-b border-line">
                      <td className="py-2 pr-3">{row.name_en}</td>
                      <td className="py-2 pr-3">{row.applications}</td>
                      <td className="py-2 pr-3">{row.checked}</td>
                      <td className="py-2">{row.average_score == null ? "—" : row.average_score.toFixed(1)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </section>
          <section className="panel">
            <h2 className="text-lg font-semibold text-navy">Daily activity</h2>
            <p className="mt-1 text-sm text-muted">Applications created in the last {stats.days} days.</p>
            <ul className="mt-4 flex items-end gap-1" aria-label="Applications created per day">
              {stats.activity.map((item) => (
                <li key={item.date} className="flex min-w-0 flex-1 flex-col items-center gap-1">
                  <span className="sr-only">
                    {item.date}: {item.count}
                  </span>
                  <span
                    className="w-full rounded-t bg-royal"
                    style={{ height: `${Math.max(4, (item.count / maxActivity) * 96)}px` }}
                    title={`${item.date}: ${item.count}`}
                  />
                </li>
              ))}
            </ul>
          </section>
          <ChecksTable rows={stats.recent_checks} />
          <p className="text-sm text-muted">{stats.footnote || STATS_FOOTNOTE}</p>
          {stats.capped ? <p className="text-sm text-saffron">These totals are capped at 5,000 recent rows.</p> : null}
        </>
      ) : null}
      {!loading ? <RetentionPanel /> : null}
    </div>
  );
}

function RetentionPanel() {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [summary, setSummary] = useState<CleanupSummary | null>(null);

  async function run(dryRun: boolean) {
    if (busy) {
      return;
    }
    if (!dryRun) {
      const confirmed = window.confirm(
        "Delete applications that have not been updated within the retention window? Storage files are removed first. This cannot be undone.",
      );
      if (!confirmed) {
        return;
      }
    }
    setBusy(true);
    setError(null);
    try {
      const token = await getAccessToken();
      if (!token) {
        setError("Please sign in again.");
        return;
      }
      setSummary(await runAdminCleanup(token, dryRun));
    } catch (caught: unknown) {
      setError(caught instanceof Error ? caught.message : "The cleanup could not be run.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="panel">
      <h2 className="text-lg font-semibold text-navy">Data retention</h2>
      <p className="mt-2 text-sm text-muted">
        Count or remove applications that have not been updated within DATA_RETENTION_DAYS. The preview is always a
        dry run. Counts only — no names, files, or paths are shown.
      </p>
      <div className="mt-4 flex flex-wrap gap-2">
        <button type="button" className="btn-secondary" onClick={() => void run(true)} disabled={busy}>
          {busy ? "Working…" : "Preview old applications"}
        </button>
        <button type="button" className="btn-secondary border-red-200 text-red-800" onClick={() => void run(false)} disabled={busy}>
          Delete expired applications
        </button>
      </div>
      {error ? <p className="mt-3 text-sm text-red-800">{error}</p> : null}
      {summary ? (
        <ul className="mt-3 text-sm text-ink">
          <li>Mode: {summary.dry_run ? "dry run" : "applied"}</li>
          <li>Days: {summary.days}</li>
          <li>Applications: {summary.applications}</li>
          <li>Files: {summary.files}</li>
          <li>Deleted applications: {summary.deleted_applications}</li>
          <li>Deleted files: {summary.deleted_files}</li>
          <li>Skipped: {summary.skipped_applications}</li>
        </ul>
      ) : null}
    </section>
  );
}

function StatCard({ label, value, hint }: { label: string; value: string; hint: string }) {
  return (
    <article className="panel">
      <p className="text-sm text-muted">{label}</p>
      <p className="mt-1 text-3xl font-semibold text-navy">{value}</p>
      <p className="mt-1 text-sm text-muted">{hint}</p>
    </article>
  );
}

function BarSlice({ label, count, total, className }: { label: string; count: number; total: number; className: string }) {
  if (count === 0) {
    return null;
  }
  return (
    <span className={`flex items-center justify-center px-2 text-xs font-semibold text-white ${className}`} style={{ width: `${(count / total) * 100}%` }}>
      {label}
    </span>
  );
}

function ChecksTable({ rows }: { rows: AdminStats["recent_checks"] }) {
  return (
    <section className="panel overflow-x-auto">
      <h2 className="text-lg font-semibold text-navy">Recent checks</h2>
      {rows.length === 0 ? (
        <p className="mt-3 text-muted">No applications yet.</p>
      ) : (
        <table className="mt-3 w-full min-w-[40rem] text-left text-sm">
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
            {rows.map((row) => (
              <tr key={row.id} className="border-b border-line">
                <td className="py-2 pr-3">{row.service_name}</td>
                <td className="py-2 pr-3">{row.user_label}</td>
                <td className="py-2 pr-3">{row.label ? labelCopy(row.label) : "—"}</td>
                <td className="py-2 pr-3">{row.score == null ? "—" : row.score}</td>
                <td className="py-2 pr-3">{row.document_count}</td>
                <td className="py-2">{row.created_at ? row.created_at.slice(0, 10) : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
