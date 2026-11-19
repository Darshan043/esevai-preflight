import Link from "next/link";
import { redirect } from "next/navigation";
import { connection } from "next/server";

import { Card } from "@/components/Card";
import { ErrorMessage } from "@/components/ErrorMessage";
import { formatStartedAt } from "@/lib/dates";
import { getRequestLanguage, listMyApplications } from "@/lib/catalog";
import { pickName } from "@/lib/language";
import { LABEL_COPY } from "@/lib/report";
import { getUserAndProfile } from "@/lib/supabase/server";

export async function DashboardContent() {
  // This page depends on the signed-in request. Wait until request time so
  // Supabase can check session expiry without running during prerender.
  await connection();
  const current = await getUserAndProfile();
  if (!current) {
    redirect("/login?next=/dashboard");
  }

  const [language, result] = await Promise.all([getRequestLanguage(), listMyApplications()]);
  const items = result.items;
  const draftCount = items.filter((item) => item.status === "draft").length;
  const checkedCount = items.filter((item) => item.status === "checked").length;
  const recent = items.slice(0, 5);
  const name = current.profile?.full_name?.trim() || "there";

  return (
    <div className="flex flex-col gap-6">
      <header className="page-banner">
        <p className="text-xs font-semibold tracking-[0.14em] text-royal uppercase">Citizen dashboard</p>
        <h1 className="mt-1 text-3xl font-semibold tracking-tight text-navy">Welcome, {name}</h1>
        <p className="mt-2 text-muted">Prepare your documents, then open a draft or start a new check.</p>
      </header>
      {result.error ? <ErrorMessage message={result.error} /> : null}
      <div className="grid gap-4 sm:grid-cols-3">
        <Card>
          <p className="text-xs font-semibold tracking-[0.12em] text-muted uppercase">Total applications</p>
          <p className="mt-2 text-3xl font-semibold text-navy">{items.length}</p>
          <p className="mt-1 text-sm text-muted">
            {items.length === 1 ? "application on this account" : "applications on this account"}
          </p>
        </Card>
        <Card>
          <p className="text-xs font-semibold tracking-[0.12em] text-muted uppercase">Drafts</p>
          <p className="mt-2 text-3xl font-semibold text-navy">{draftCount}</p>
          <p className="mt-1 text-sm text-muted">Still being prepared</p>
        </Card>
        <Card>
          <p className="text-xs font-semibold tracking-[0.12em] text-muted uppercase">Checked</p>
          <p className="mt-2 text-3xl font-semibold text-navy">{checkedCount}</p>
          <p className="mt-1 text-sm text-muted">Readiness report generated</p>
        </Card>
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <Card className="service-card">
          <h2 className="text-lg font-semibold text-navy">Browse services</h2>
          <p className="mt-2 text-sm leading-6 text-muted">See the documents required for each service.</p>
          <Link href="/services" className="btn-primary mt-4">
            Browse services
          </Link>
        </Card>
        <Card className="service-card">
          <h2 className="text-lg font-semibold text-navy">My applications</h2>
          <p className="mt-2 text-sm leading-6 text-muted">Open a document check you already started.</p>
          <Link href="/applications" className="btn-primary mt-4">
            My applications
          </Link>
        </Card>
      </div>
      <section className="flex flex-col gap-4">
        <h2 className="section-title">Recent applications</h2>
        {recent.length === 0 ? (
          <Card>
            <p className="text-sm text-muted">You have not started a document check yet.</p>
            <Link href="/services" className="btn-primary mt-4">
              Browse services
            </Link>
          </Card>
        ) : (
          <ul className="flex flex-col gap-3">
            {recent.map((item) => (
              <li key={item.id}>
                <Card className="service-card">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <h3 className="text-lg font-semibold text-navy">{pickName(item.serviceName, language)}</h3>
                    <p className="rounded-full bg-sky px-3 py-1 text-sm font-medium text-navy">
                      {item.status === "checked" ? "Checked" : "Draft"}
                    </p>
                  </div>
                  <p className="mt-2 text-sm text-ink">Started {formatStartedAt(item.created_at)}</p>
                  {item.readiness_score != null && item.label ? (
                    <p className="mt-1 text-sm text-ink">
                      Score {item.readiness_score} · {LABEL_COPY[item.label].title}
                    </p>
                  ) : (
                    <p className="mt-1 text-sm text-muted">Not checked yet</p>
                  )}
                  <Link href={`/applications/${item.id}`} className="btn-secondary mt-4">
                    Open
                  </Link>
                </Card>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
