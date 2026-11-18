import { Suspense } from "react";

import { AdminGate } from "@/app/admin/admin-gate";

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return (
    <main className="page-wrap max-w-6xl">
      <Suspense fallback={<p className="text-muted">Loading the admin page...</p>}>
        <AdminGate>{children}</AdminGate>
      </Suspense>
    </main>
  );
}
