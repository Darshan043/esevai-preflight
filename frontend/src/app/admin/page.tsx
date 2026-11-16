import { Suspense } from "react";

import { AdminContent } from "@/app/admin/admin-content";

export default function AdminPage() {
  return (
    <main className="mx-auto flex w-full max-w-2xl flex-col px-6 py-12">
      <Suspense fallback={<p className="text-zinc-600">Loading the admin page...</p>}>
        <AdminContent />
      </Suspense>
    </main>
  );
}
