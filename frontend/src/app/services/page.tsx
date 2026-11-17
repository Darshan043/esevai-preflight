import Link from "next/link";
import { Suspense } from "react";

import { Card } from "@/components/Card";
import { EmptyState } from "@/components/EmptyState";
import { ErrorMessage } from "@/components/ErrorMessage";
import { LoadingSkeleton } from "@/components/LoadingSkeleton";
import { PageContainer } from "@/components/PageContainer";
import { getRequestLanguage, listServices } from "@/lib/catalog";
import { pickName } from "@/lib/language";

async function ServiceList() {
  const [language, result] = await Promise.all([getRequestLanguage(), listServices()]);
  if (result.error) {
    return <ErrorMessage message={result.error} />;
  }
  if (result.items.length === 0) {
    return (
      <EmptyState
        title="No services yet"
        message="There are no active services to prepare for right now."
      />
    );
  }

  return (
    <ul className="grid gap-4">
      {result.items.map((service) => (
        <li key={service.id}>
          <Card>
            <h2 className="text-xl font-semibold text-zinc-900">{pickName(service, language)}</h2>
            {service.description ? <p className="mt-2 text-zinc-600">{service.description}</p> : null}
            <p className="mt-3 text-sm text-zinc-700">
              {service.documentCount} required document{service.documentCount === 1 ? "" : "s"}
            </p>
            {service.is_verified ? (
              <p className="mt-2 text-sm font-medium text-green-800">Verified</p>
            ) : (
              <p className="mt-2 text-sm text-amber-800" title="Draft list – confirm on the official portal">
                Draft list – confirm on the official portal
              </p>
            )}
            <Link
              href={`/services/${service.slug}`}
              className="mt-4 inline-flex min-h-11 items-center rounded-md bg-zinc-900 px-4 text-sm font-medium text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-zinc-900"
            >
              View details
            </Link>
          </Card>
        </li>
      ))}
    </ul>
  );
}

export default function ServicesPage() {
  return (
    <PageContainer>
      <header>
        <h1 className="text-3xl font-semibold tracking-tight text-zinc-900">Services</h1>
        <p className="mt-2 text-zinc-600">Choose a service and check the documents you will need.</p>
      </header>
      <Suspense fallback={<LoadingSkeleton label="Loading services" />}>
        <ServiceList />
      </Suspense>
    </PageContainer>
  );
}
