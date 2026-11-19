import { forbidden, redirect } from "next/navigation";
import { connection } from "next/server";

import { adminPageDecision } from "@/lib/admin-access";
import { getUserAndProfile } from "@/lib/supabase/server";

export async function requireAdminPage(): Promise<void> {
  // Wait until request time so the role is read for this visitor, not at build time.
  await connection();
  const current = await getUserAndProfile();
  const decision = adminPageDecision({
    signedIn: current !== null,
    role: current?.profile?.role ?? null,
    profileFound: current?.profile != null,
    profileLookupFailed: current?.profileError === true,
  });
  if (decision === "login") {
    redirect("/login?next=/admin");
  }
  if (decision === "forbidden") {
    forbidden();
  }
}
