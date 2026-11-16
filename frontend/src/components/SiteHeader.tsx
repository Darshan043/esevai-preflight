// Shared navigation. The role comes from the signed-in user's own profile row.

import Link from "next/link";

import { SignOutButton } from "@/components/SignOutButton";
import { getUserAndProfile } from "@/lib/supabase/server";

export async function SiteHeader() {
  const current = await getUserAndProfile();
  const signedIn = current !== null;
  const isAdmin = current?.profile?.role === "admin";

  return (
    <header className="border-b border-zinc-200 bg-white">
      <div className="mx-auto flex w-full max-w-3xl flex-wrap items-center gap-3 px-6 py-4">
        <Link href="/" className="text-base font-semibold text-zinc-900">
          e-Sevai Pre-Flight
        </Link>
        <nav className="flex flex-wrap items-center gap-3 text-sm text-zinc-700">
          <Link href="/">Home</Link>
          {signedIn ? <Link href="/dashboard">Dashboard</Link> : null}
          {isAdmin ? <Link href="/admin">Admin</Link> : null}
        </nav>
        <div className="ml-auto flex flex-wrap items-center gap-2">
          {signedIn ? (
            <SignOutButton />
          ) : (
            <>
              <Link href="/login" className="rounded-md px-3 py-2 text-sm text-zinc-800">
                Login
              </Link>
              <Link href="/signup" className="rounded-md bg-zinc-900 px-3 py-2 text-sm text-white">
                Sign up
              </Link>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
