import { Suspense } from "react";

import { DashboardContent } from "@/app/dashboard/dashboard-content";

export default function DashboardPage() {
  return (
    <main className="mx-auto flex w-full max-w-2xl flex-col px-6 py-12">
      <Suspense fallback={<p className="text-zinc-600">Loading your dashboard...</p>}>
        <DashboardContent />
      </Suspense>
    </main>
  );
}
