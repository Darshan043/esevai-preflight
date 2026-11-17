import Link from "next/link";
import { redirect } from "next/navigation";
import { Suspense } from "react";

import { DeleteApplicationButton } from "@/components/DeleteApplicationButton";
import { Card } from "@/components/Card";
import { EmptyState } from "@/components/EmptyState";
import { ErrorMessage } from "@/components/ErrorMessage";
import { LoadingSkeleton } from "@/components/LoadingSkeleton";
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
              <Card>
                <h2 className="text-xl font-semibold text-zinc-900">{pickName(item.serviceName, language)}</h2>
                <p className="mt-2 text-sm text-zinc-700">Started {item.created_at.slice(0, 10)}</p>
                <p className="mt-1 text-sm text-zinc-700">Status: {item.status === "checked" ? "Checked" : "Draft"}</p>
                {item.readiness_score != null ? (
                  <p className="mt-1 text-sm text-zinc-700">Readiness score: {item.readiness_score}</p>
                ) : null}
                <p className="mt-1 text-sm text-zinc-700">
                  {item.uploadedCount} of {item.requiredCount} required documents uploaded
                </p>
                <div className="mt-4 flex flex-wrap gap-3">
                  <Link
                    href={`/applications/${item.id}`}
                    className="inline-flex min-h-11 items-center rounded-md bg-zinc-900 px-4 text-sm font-medium text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-zinc-900"
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
      <header>
        <h1 className="text-3xl font-semibold tracking-tight text-zinc-900">My applications</h1>
        <p className="mt-2 text-zinc-600">Open a draft or start again from the service list.</p>
      </header>
      <Suspense fallback={<LoadingSkeleton label="Loading applications" />}>
        <ApplicationList searchParams={searchParams} />
      </Suspense>
    </PageContainer>
  );
}
