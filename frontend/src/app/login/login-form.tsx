"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useState, type FormEvent } from "react";

import { createClient } from "@/lib/supabase/client";

function safeNextPath(value: string | null): string {
  // Only allow a local path, so a query string cannot send the browser off this site.
  if (!value || !value.startsWith("/") || value.startsWith("//") || value.includes("\\")) {
    return "/dashboard";
  }
  return value;
}

export function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    if (!email.trim() || !password) {
      setError("Enter your email and password.");
      return;
    }

    setPending(true);
    const supabase = createClient();
    const { error: signInError } = await supabase.auth.signInWithPassword({
      email: email.trim(),
      password,
    });
    setPending(false);

    if (signInError) {
      // One message for a wrong email and a wrong password, so the form does not reveal which one.
      setError("Email or password is incorrect.");
      return;
    }

    router.push(safeNextPath(searchParams.get("next")));
    router.refresh();
  }

  return (
    <form onSubmit={(event) => void onSubmit(event)} className="rounded-xl border border-zinc-200 bg-white p-6 shadow-sm">
      <h1 className="text-2xl font-semibold text-zinc-900">Login</h1>
      <label className="mt-4 block text-sm font-medium text-zinc-800" htmlFor="email">
        Email
        <input
          id="email"
          type="email"
          autoComplete="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          className="mt-1 w-full rounded-md border border-zinc-300 px-3 py-2"
        />
      </label>
      <label className="mt-4 block text-sm font-medium text-zinc-800" htmlFor="password">
        Password
        <input
          id="password"
          type="password"
          autoComplete="current-password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          className="mt-1 w-full rounded-md border border-zinc-300 px-3 py-2"
        />
      </label>
      {error ? <p className="mt-4 text-sm text-red-600">{error}</p> : null}
      <button
        type="submit"
        disabled={pending}
        className="mt-6 rounded-md bg-zinc-900 px-4 py-2 text-sm text-white disabled:opacity-60"
      >
        {pending ? "Signing in..." : "Login"}
      </button>
    </form>
  );
}
