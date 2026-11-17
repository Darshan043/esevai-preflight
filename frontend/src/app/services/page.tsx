import { Suspense } from "react";

import { EmptyState } from "@/components/EmptyState";
import { ErrorMessage } from "@/components/ErrorMessage";
import { LoadingSkeleton } from "@/components/LoadingSkeleton";
import { PageBanner } from "@/components/PageBanner";
import { PageContainer } from "@/components/PageContainer";
import { ServiceCatalog } from "@/components/ServiceCatalog";
import { getRequestLanguage, listServices } from "@/lib/catalog";
import { pickName } from "@/lib/language";

async function ServiceList() {
  const [language, result] = await Promise.all([getRequestLanguage(), listServices()]);
  if (result.error) {
    return <ErrorMessage message={result.error} />;
  }
  if (result.items.length === 0) {
    return (
      <EmptyState title="No services yet" message="There are no active services to prepare for right now." />
    );
  }

  return (
    <ServiceCatalog
      items={result.items.map((service) => ({
        id: service.id,
        slug: service.slug,
        name: pickName(service, language),
        description: service.description,
        documentCount: service.documentCount,
        isVerified: service.is_verified,
      }))}
    />
  );
}

export default function ServicesPage() {
  return (
    <PageContainer>
      <PageBanner kicker="Service catalogue" title="Services">
        Choose a service and check the documents you will need.
      </PageBanner>
      <Suspense fallback={<LoadingSkeleton label="Loading services" />}>
        <ServiceList />
      </Suspense>
    </PageContainer>
  );
}
