import Link from "next/link";
import { redirect } from "next/navigation";
import { Suspense } from "react";

import { DeleteApplicationButton } from "@/components/DeleteApplicationButton";
import { Card } from "@/components/Card";
import { EmptyState } from "@/components/EmptyState";
import { ErrorMessage } from "@/components/ErrorMessage";
import { LoadingSkeleton } from "@/components/LoadingSkeleton";
import { PageBanner } from "@/components/PageBanner";
import { PageContainer } from "@/components/PageContainer";
import { getRequestLanguage, listMyApplications } from "@/lib/catalog";
import { pickName } from "@/lib/language";
import { getUserAndProfile } from "@/lib/supabase/server";

async function ApplicationList({ searchParams }: { searchParams: Promise<{ error?: string | string[] }> }) {
  const current = await getUserAndProfile();
  if (!current) {
    redirect("/login?next=/applications");
  }

  const query = await searchParams;
  const [language, result] = await Promise.all([getRequestLanguage(), listMyApplications()]);

  return (
    <>
      {query.error === "delete" ? (
        <p className="rounded-md border border-red-200 bg-red-50 p-4 text-red-800" role="alert">
          We could not delete that application. Please try again.
        </p>
      ) : null}
      {result.error ? <ErrorMessage message={result.error} /> : null}
      {!result.error && result.items.length === 0 ? (
        <EmptyState
          title="No applications yet"
          message="Start a document check from the service list."
          actionHref="/services"
          actionLabel="Browse services"
        />
      ) : null}
      {!result.error && result.items.length > 0 ? (
        <ul className="flex flex-col gap-4">
          {result.items.map((item) => (
            <li key={item.id}>
              <Card className="service-card">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <h2 className="text-xl font-semibold text-navy">{pickName(item.serviceName, language)}</h2>
                  <p className="rounded-full bg-sky px-3 py-1 text-sm font-medium text-navy">
                    {item.status === "checked" ? "Checked" : "Draft"}
                  </p>
                </div>
                <p className="mt-3 text-sm text-ink">Started {item.created_at.slice(0, 10)}</p>
                {item.readiness_score != null ? (
                  <p className="mt-1 text-sm text-ink">Readiness score: {item.readiness_score}</p>
                ) : null}
                <p className="mt-1 text-sm text-ink">
                  {item.uploadedCount} of {item.requiredCount} required documents uploaded
                </p>
                <div className="mt-4 flex flex-wrap gap-3">
                  <Link
                    href={`/applications/${item.id}`}
                    className="btn-primary"
                  >
                    Open
                  </Link>
                  <DeleteApplicationButton applicationId={item.id} />
                </div>
              </Card>
            </li>
          ))}
        </ul>
      ) : null}
    </>
  );
}

export default function ApplicationsPage({
  searchParams,
}: {
  searchParams: Promise<{ error?: string | string[] }>;
}) {
  return (
    <PageContainer>
      <PageBanner kicker="Your account" title="My applications">
        Open a draft or start again from the service list.
      </PageBanner>
      <Suspense fallback={<LoadingSkeleton label="Loading applications" />}>
        <ApplicationList searchParams={searchParams} />
      </Suspense>
    </PageContainer>
  );
}
