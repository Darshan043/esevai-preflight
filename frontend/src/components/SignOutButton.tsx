"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { createClient } from "@/lib/supabase/client";

export function SignOutButton() {
  const router = useRouter();
  const [pending, setPending] = useState(false);

  async function signOut() {
    setPending(true);
    const supabase = createClient();
    await supabase.auth.signOut();
    router.push("/");
    router.refresh();
  }

  return (
    <button
      type="button"
      onClick={() => {
        void signOut();
      }}
      disabled={pending}
      className="rounded-md border border-zinc-300 px-3 py-2 text-sm text-zinc-800 disabled:opacity-60"
    >
      {pending ? "Signing out..." : "Sign out"}
    </button>
  );
}
