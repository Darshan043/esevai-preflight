"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { createClient } from "@/lib/supabase/client";

const SIGN_OUT_WAIT_MS = 8000;

export function SignOutButton() {
  const router = useRouter();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function goToLogin() {
    router.replace("/login");
    router.refresh();
  }

  async function stillSignedIn() {
    const supabase = createClient();
    const check = supabase.auth.getUser().then((result) => Boolean(result.data.user));
    const timedOut = new Promise<boolean>((resolve) => {
      window.setTimeout(() => resolve(true), SIGN_OUT_WAIT_MS);
    });
    return Promise.race([check, timedOut]);
  }

  async function signOut() {
    setPending(true);
    setError(null);
    const supabase = createClient();
    try {
      // Clear this browser first. A global logout waits for the server and
      // keeps the session when that request fails, which leaves the button stuck.
      const signOutPromise = supabase.auth.signOut({ scope: "local" });
      const timeout = new Promise<"timeout">((resolve) => {
        window.setTimeout(() => resolve("timeout"), SIGN_OUT_WAIT_MS);
      });
      await Promise.race([signOutPromise, timeout]);
      if (await stillSignedIn()) {
        setError("We could not sign you out. Please try again.");
        return;
      }
      goToLogin();
    } catch {
      try {
        if (!(await stillSignedIn())) {
          goToLogin();
          return;
        }
      } catch {
        // The session check failed as well. Ask the user to try again.
      }
      setError("We could not sign you out. Please try again.");
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="flex flex-col items-start gap-2">
      <button
        type="button"
        onClick={() => {
          void signOut();
        }}
        disabled={pending}
        className="btn-secondary"
      >
        {pending ? "Signing out..." : "Sign out"}
      </button>
      {error ? (
        <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-800" role="alert">
          {error}
        </p>
      ) : null}
    </div>
  );
}
