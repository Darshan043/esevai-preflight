import { Suspense } from "react";

import { DashboardContent } from "@/app/dashboard/dashboard-content";

export default function DashboardPage() {
  return (
    <main className="page-wrap max-w-5xl">
      <Suspense fallback={<p className="text-muted">Loading your dashboard...</p>}>
        <DashboardContent />
      </Suspense>
    </main>
  );
}
