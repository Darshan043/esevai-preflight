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
      <header className="page-banner">
        <p className="text-xs font-semibold tracking-[0.14em] text-royal uppercase">Citizen dashboard</p>
        <h1 className="mt-1 text-3xl font-semibold tracking-tight text-navy">Welcome, {name}</h1>
        <p className="mt-2 text-muted">{current.email ?? "No email on this account"}</p>
      </header>
      <div className="grid gap-4 sm:grid-cols-3">
        <Card>
          <p className="text-xs font-semibold tracking-[0.12em] text-muted uppercase">Applications</p>
          <p className="mt-2 text-3xl font-semibold text-navy">{applicationCount}</p>
          <p className="mt-1 text-sm text-muted">
            {applicationCount === 1 ? "application on this account" : "applications on this account"}
          </p>
        </Card>
        <Card>
          <p className="text-xs font-semibold tracking-[0.12em] text-muted uppercase">Account role</p>
          <p className="mt-2 text-xl font-semibold text-navy capitalize">{role}</p>
          <p className="mt-1 text-sm text-muted">Taken from your profile</p>
        </Card>
        <Card>
          <p className="text-xs font-semibold tracking-[0.12em] text-muted uppercase">Language</p>
          <p className="mt-2 text-xl font-semibold text-navy">English / Tamil</p>
          <p className="mt-1 text-sm text-muted">Switch document names from the menu</p>
        </Card>
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <Card className="service-card">
          <h2 className="text-lg font-semibold text-navy">Browse services</h2>
          <p className="mt-2 text-sm leading-6 text-muted">See the services you can prepare for.</p>
          <Link href="/services" className="btn-primary mt-4">
            Browse services
          </Link>
        </Card>
        <Card className="service-card">
          <h2 className="text-lg font-semibold text-navy">My applications</h2>
          <p className="mt-2 text-sm leading-6 text-muted">Open a document check you already started.</p>
          <Link href="/applications" className="btn-primary mt-4">
            My applications
          </Link>
        </Card>
      </div>
      <BackendConnection />
      <SignOutButton />
    </div>
  );
}
