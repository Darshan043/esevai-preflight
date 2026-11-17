import { Suspense } from "react";

import { AdminContent } from "@/app/admin/admin-content";

export default function AdminPage() {
  return (
    <main className="page-wrap max-w-3xl">
      <Suspense fallback={<p className="text-muted">Loading the admin page...</p>}>
        <AdminContent />
      </Suspense>
    </main>
  );
}
