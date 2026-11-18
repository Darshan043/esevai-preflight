import { notFound, redirect } from "next/navigation";
import { Suspense } from "react";

import { ErrorMessage } from "@/components/ErrorMessage";
import { LoadingSkeleton } from "@/components/LoadingSkeleton";
import { PageContainer } from "@/components/PageContainer";
import { ReadinessReport } from "@/components/ReadinessReport";
import { getChecklist, getRequestLanguage } from "@/lib/catalog";
import { getUserAndProfile } from "@/lib/supabase/server";

async function ReportBody({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const current = await getUserAndProfile();
  if (!current) {
    redirect(`/login?next=/applications/${id}/report`);
  }

  const [language, result] = await Promise.all([getRequestLanguage(), getChecklist(id)]);
  if (result.error) {
    return <ErrorMessage message={result.error} />;
  }
  if (!result.data) {
    notFound();
  }

  return (
    <ReadinessReport
      applicationId={result.data.application.id}
      serviceName={result.data.service}
      language={language}
    />
  );
}

export default function ReportPage({ params }: { params: Promise<{ id: string }> }) {
  return (
    <PageContainer>
      <Suspense fallback={<LoadingSkeleton label="Loading report" />}>
        <ReportBody params={params} />
      </Suspense>
    </PageContainer>
  );
}
