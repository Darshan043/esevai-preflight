import Link from "next/link";
import { connection } from "next/server";

import { getUserAndProfile } from "@/lib/supabase/server";

const primaryClass =
  "inline-flex min-h-11 items-center rounded-md bg-zinc-900 px-4 text-sm font-medium text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-zinc-900";
const secondaryClass =
  "inline-flex min-h-11 items-center rounded-md border border-zinc-300 px-4 text-sm font-medium text-zinc-800 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-zinc-900";

export async function HomeActions() {
  // These buttons depend on the signed-in request. Wait until request time so
  // Supabase can check session expiry without running during prerender.
  await connection();
  const current = await getUserAndProfile();

  return (
    <div className="flex flex-wrap gap-3">
      <Link href="/services" className={primaryClass}>
        Browse services
      </Link>
      {current ? (
        <Link href="/applications" className={secondaryClass}>
          My applications
        </Link>
      ) : (
        <Link href="/signup" className={secondaryClass}>
          Create account
        </Link>
      )}
    </div>
  );
}
