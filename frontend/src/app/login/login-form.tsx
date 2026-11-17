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
    <form onSubmit={(event) => void onSubmit(event)} className="panel">
      <p className="text-sm font-semibold text-royal">Account</p>
      <h1 className="mt-1 text-2xl font-semibold text-navy">Login</h1>
      <p className="mt-2 text-sm text-muted">Use the email and password for your e-Sevai Pre-Flight account.</p>
      <label className="mt-4 block text-sm font-medium text-navy" htmlFor="email">
        Email
        <input
          id="email"
          type="email"
          autoComplete="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          className="field"
        />
      </label>
      <label className="mt-4 block text-sm font-medium text-navy" htmlFor="password">
        Password
        <input
          id="password"
          type="password"
          autoComplete="current-password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          className="field"
        />
      </label>
      {error ? <p className="mt-4 text-sm text-red-700">{error}</p> : null}
      <button type="submit" disabled={pending} className="btn-primary mt-6 w-full">
        {pending ? "Signing in..." : "Login"}
      </button>
    </form>
  );
}
