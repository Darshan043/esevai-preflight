"use client";

// Reads the session after the page is in the browser.
// The first render always shows the logged-out links so prerender stays stable.

import Link from "next/link";
import { useEffect, useState } from "react";

import { SignOutButton } from "@/components/SignOutButton";
import { createClient } from "@/lib/supabase/client";

type HeaderState = "logged-out" | "logged-in";

export function HeaderAuth() {
  const [state, setState] = useState<HeaderState>("logged-out");
  const [isAdmin, setIsAdmin] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function loadSession() {
      try {
        const supabase = createClient();
        const { data, error } = await supabase.auth.getUser();
        if (cancelled) {
          return;
        }
        if (error || !data.user) {
          setIsAdmin(false);
          setState("logged-out");
          return;
        }

        const { data: profile, error: profileError } = await supabase
          .from("profiles")
          .select("role")
          .eq("id", data.user.id)
          .maybeSingle();
        if (cancelled) {
          return;
        }
        // A failed profile read must not show the admin link.
        setIsAdmin(!profileError && profile?.role === "admin");
        setState("logged-in");
      } catch {
        if (!cancelled) {
          setIsAdmin(false);
          setState("logged-out");
        }
      }
    }

    void loadSession();
    return () => {
      cancelled = true;
    };
  }, []);

  const signedIn = state === "logged-in";

  return (
    <>
      <nav className="flex flex-wrap items-center gap-3 text-sm text-zinc-700">
        <Link href="/">Home</Link>
        {signedIn ? <Link href="/dashboard">Dashboard</Link> : null}
        {signedIn && isAdmin ? <Link href="/admin">Admin</Link> : null}
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
    </>
  );
}
