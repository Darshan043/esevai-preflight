import { redirect } from "next/navigation";
import { connection } from "next/server";

import { AdminNav } from "@/components/admin/AdminNav";
import { getUserAndProfile } from "@/lib/supabase/server";

export async function AdminGate({ children }: { children: React.ReactNode }) {
  // This page depends on the signed-in request. Wait until request time so
  // Supabase can check session expiry without running during prerender.
  await connection();
  const current = await getUserAndProfile();
  if (!current) {
    redirect("/login?next=/admin");
  }

  // A citizen gets only this message. The admin screens are not rendered for them.
  if (current.profile?.role !== "admin") {
    return (
      <section className="page-banner">
        <p className="text-xs font-semibold tracking-[0.14em] text-royal uppercase">Administration</p>
        <h1 className="mt-1 text-2xl font-semibold text-navy">Access denied</h1>
        <p className="mt-2 text-muted">This page is only for admin accounts.</p>
      </section>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <AdminNav />
      {children}
    </div>
  );
}
