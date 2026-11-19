import Link from "next/link";
import { connection } from "next/server";

import { getUserAndProfile } from "@/lib/supabase/server";

const primaryClass = "btn-on-dark";
const secondaryClass = "btn-on-dark-ghost";

export async function HomeActions() {
  // These buttons depend on the signed-in request. Wait until request time so
  // Supabase can check session expiry without running during prerender.
  await connection();
  const current = await getUserAndProfile();

  return (
    <div className="flex flex-wrap gap-3">
      <Link href="/services" className={primaryClass}>
        Check Your Documents
      </Link>
      {current ? (
        <Link href="/dashboard" className={secondaryClass}>
          Open dashboard
        </Link>
      ) : (
        <Link href="/signup" className={secondaryClass}>
          Create account
        </Link>
      )}
    </div>
  );
}
