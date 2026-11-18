import Link from "next/link";
import { notFound } from "next/navigation";
import { Suspense } from "react";

import { startNewCheck } from "@/app/services/[slug]/actions";
import { Card } from "@/components/Card";
import { Disclaimer } from "@/components/Disclaimer";
import { ErrorMessage } from "@/components/ErrorMessage";
import { LoadingSkeleton } from "@/components/LoadingSkeleton";
import { PageContainer } from "@/components/PageContainer";
import { getRequestLanguage, getServiceBySlug, latestDraftId } from "@/lib/catalog";
import { pickName } from "@/lib/language";
import { getUserAndProfile } from "@/lib/supabase/server";

// Unknown slugs must answer 404 before the page starts streaming.
export const instant = false;

const buttonClass = "btn-primary";
const secondaryClass = "btn-secondary";

function validityText(days: number | null): string | null {
  if (days == null) {
    return null;
  }
  return days === 1
    ? "Use a document from the last 1 day."
    : `Use a document from the last ${days} days.`;
}

async function ServiceDetail({
  service,
  documents,
  searchParams,
}: {
  service: NonNullable<Awaited<ReturnType<typeof getServiceBySlug>>["service"]>;
  documents: Awaited<ReturnType<typeof getServiceBySlug>>["documents"];
  searchParams: Promise<{ error?: string | string[] }>;
}) {
  const query = await searchParams;
  const errorCode = Array.isArray(query.error) ? query.error[0] : query.error;
  const startFailed = errorCode === "start";
  const [language, current] = await Promise.all([getRequestLanguage(), getUserAndProfile()]);
  const draftId = current ? await latestDraftId(service.id, current.userId) : null;

  return (
    <>
      <header className="page-banner">
        <p className="text-xs font-semibold tracking-[0.14em] text-royal uppercase">Service details</p>
        <h1 className="mt-1 text-3xl font-semibold tracking-tight text-navy">{pickName(service, language)}</h1>
        {service.description ? <p className="mt-2 max-w-3xl leading-7 text-muted">{service.description}</p> : null}
        {service.is_verified ? (
          <p className="mt-3 text-sm font-medium text-india">Verified</p>
        ) : (
          <p className="mt-3 text-sm text-saffron">Draft list – confirm on the official portal</p>
        )}
      </header>
      <Disclaimer />
      {startFailed ? (
        <p className="rounded-md border border-red-200 bg-red-50 p-4 text-red-800" role="alert">
          We could not start your document check. Please try again.
        </p>
      ) : null}
      {errorCode === "inactive" ? (
        <p className="rounded-md border border-red-200 bg-red-50 p-4 text-red-800" role="alert">
          This service is not accepting new checks. Open an existing application from My applications if you already started one.
        </p>
      ) : null}
      <section className="flex flex-col gap-4">
        <h2 className="section-title">Documents you need</h2>
        <ul className="flex flex-col gap-4" data-required-count={documents.length}>
          {documents.map((document, index) => {
            const validity = validityText(document.validity_days);
            return (
              <li key={document.id}>
                <Card className="service-card">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <h3 className="text-lg font-semibold text-navy">
                      <span className="mr-2 text-sm font-semibold text-royal">{index + 1}.</span>
                      {pickName(document, language)}
                    </h3>
                    <p className="rounded-full bg-sky px-3 py-1 text-sm font-medium text-navy">
                      {document.is_mandatory ? "Mandatory" : "Optional"}
                    </p>
                  </div>
                  {document.description ? <p className="mt-2 text-muted">{document.description}</p> : null}
                  <p className="mt-2 text-sm text-ink">
                    Accepted formats: {document.accepted_formats.join(", ")}
                  </p>
                  <p className="mt-1 text-sm text-ink">Maximum size: {document.max_size_mb} MB</p>
                  {validity ? <p className="mt-1 text-sm text-ink">{validity}</p> : null}
                </Card>
              </li>
            );
          })}
        </ul>
      </section>
      <div className="flex flex-wrap gap-3">
        {current ? (
          <>
            {draftId ? (
              <Link href={`/applications/${draftId}`} className={buttonClass}>
                Continue your draft
              </Link>
            ) : null}
            <form action={startNewCheck.bind(null, service.id, service.slug)}>
              <button type="submit" className={draftId ? secondaryClass : buttonClass}>
                {draftId ? "Start a new check" : "Start document check"}
              </button>
            </form>
          </>
        ) : (
          <Link href={`/login?next=/services/${service.slug}`} className={buttonClass}>
            Start document check
          </Link>
        )}
      </div>
    </>
  );
}

export default async function ServicePage({
  params,
  searchParams,
}: {
  params: Promise<{ slug: string }>;
  searchParams: Promise<{ error?: string | string[] }>;
}) {
  // Look up the service before the page streams so an unknown slug can return 404.
  const { slug } = await params;
  const result = await getServiceBySlug(slug);
  if (result.error) {
    return (
      <PageContainer>
        <ErrorMessage message={result.error} />
      </PageContainer>
    );
  }
  if (!result.service) {
    notFound();
  }

  return (
    <PageContainer>
      <Suspense fallback={<LoadingSkeleton label="Loading service" />}>
        <ServiceDetail
          service={result.service}
          documents={result.documents}
          searchParams={searchParams}
        />
      </Suspense>
    </PageContainer>
  );
}
