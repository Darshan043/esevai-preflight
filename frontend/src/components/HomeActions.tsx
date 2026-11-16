import Link from "next/link";

import { getUserAndProfile } from "@/lib/supabase/server";

export async function HomeActions() {
  const current = await getUserAndProfile();

  if (current) {
    return (
      <Link href="/dashboard" className="inline-block rounded-md bg-zinc-900 px-4 py-2 text-sm text-white">
        Go to dashboard
      </Link>
    );
  }

  return (
    <div className="flex flex-wrap gap-3">
      <Link href="/login" className="rounded-md bg-zinc-900 px-4 py-2 text-sm text-white">
        Login
      </Link>
      <Link href="/signup" className="rounded-md border border-zinc-300 px-4 py-2 text-sm text-zinc-800">
        Sign up
      </Link>
    </div>
  );
}
