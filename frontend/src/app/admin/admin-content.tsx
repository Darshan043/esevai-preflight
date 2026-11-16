import { redirect } from "next/navigation";
import { connection } from "next/server";

import { AdminPing } from "@/components/AdminPing";
import { getUserAndProfile } from "@/lib/supabase/server";

export async function AdminContent() {
  // This page depends on the signed-in request. Wait until request time so
  // Supabase can check session expiry without running during prerender.
  await connection();
  const current = await getUserAndProfile();
  if (!current) {
    redirect("/login?next=/admin");
  }

  // A citizen gets only this message. The admin check is not rendered for them.
  if (current.profile?.role !== "admin") {
    return (
      <section className="rounded-xl border border-zinc-200 bg-white p-6 shadow-sm">
        <h1 className="text-2xl font-semibold text-zinc-900">Access denied</h1>
        <p className="mt-2 text-zinc-600">This page is only for admin accounts.</p>
      </section>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-3xl font-semibold tracking-tight text-zinc-900">Admin area</h1>
      <AdminPing />
    </div>
  );
}
