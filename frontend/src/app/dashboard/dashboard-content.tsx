import { redirect } from "next/navigation";
import { connection } from "next/server";

import { BackendConnection } from "@/components/BackendConnection";
import { SignOutButton } from "@/components/SignOutButton";
import { getUserAndProfile } from "@/lib/supabase/server";

export async function DashboardContent() {
  // This page depends on the signed-in request. Wait until request time so
  // Supabase can check session expiry without running during prerender.
  await connection();
  const current = await getUserAndProfile();
  if (!current) {
    redirect("/login?next=/dashboard");
  }

  const name = current.profile?.full_name?.trim() || "there";
  const role = current.profile?.role ?? "citizen";

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight text-zinc-900">Welcome, {name}</h1>
        <p className="mt-2 text-zinc-600">{current.email ?? "No email on this account"}</p>
        <p className="mt-3 inline-block rounded-full bg-zinc-100 px-3 py-1 text-sm text-zinc-800">{role}</p>
      </div>
      <BackendConnection />
      <SignOutButton />
    </div>
  );
}
