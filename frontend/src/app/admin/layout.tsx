import { Suspense } from "react";

export const instant = false;

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return (
    <main className="page-wrap max-w-6xl">
      <Suspense fallback={<p className="text-muted">Loading the admin page...</p>}>{children}</Suspense>
    </main>
  );
}
