import Link from "next/link";
import { redirect } from "next/navigation";
import { connection } from "next/server";

import { BackendConnection } from "@/components/BackendConnection";
import { Card } from "@/components/Card";
import { SignOutButton } from "@/components/SignOutButton";
import { countMyApplications } from "@/lib/catalog";
import { getUserAndProfile } from "@/lib/supabase/server";

export async function DashboardContent() {
  // This page depends on the signed-in request. Wait until request time so
  // Supabase can check session expiry without running during prerender.
  await connection();
  const current = await getUserAndProfile();
  if (!current) {
    redirect("/login?next=/dashboard");
  }
  const applicationCount = await countMyApplications();

  const name = current.profile?.full_name?.trim() || "there";
  const role = current.profile?.role ?? "citizen";

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight text-zinc-900">Welcome, {name}</h1>
        <p className="mt-2 text-zinc-600">{current.email ?? "No email on this account"}</p>
        <p className="mt-3 inline-block rounded-full bg-zinc-100 px-3 py-1 text-sm text-zinc-800">{role}</p>
      </div>
      <p className="text-zinc-700">
        You have {applicationCount} application{applicationCount === 1 ? "" : "s"}.
      </p>
      <div className="grid gap-4 sm:grid-cols-2">
        <Card>
          <h2 className="text-lg font-semibold text-zinc-900">Browse services</h2>
          <p className="mt-2 text-sm text-zinc-600">See the services you can prepare for.</p>
          <Link
            href="/services"
            className="mt-4 inline-flex min-h-11 items-center rounded-md bg-zinc-900 px-4 text-sm font-medium text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-zinc-900"
          >
            Browse services
          </Link>
        </Card>
        <Card>
          <h2 className="text-lg font-semibold text-zinc-900">My applications</h2>
          <p className="mt-2 text-sm text-zinc-600">Open a document check you already started.</p>
          <Link
            href="/applications"
            className="mt-4 inline-flex min-h-11 items-center rounded-md bg-zinc-900 px-4 text-sm font-medium text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-zinc-900"
          >
            My applications
          </Link>
        </Card>
      </div>
      <BackendConnection />
      <SignOutButton />
    </div>
  );
}
