"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { createClient } from "@/lib/supabase/client";

export function SignupForm() {
  const router = useRouter();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setInfo(null);

    if (!fullName.trim()) {
      setError("Enter your full name.");
      return;
    }
    if (!email.trim()) {
      setError("Enter your email.");
      return;
    }
    if (password.length < 8) {
      setError("Use a password with at least 8 characters.");
      return;
    }
    if (password !== confirmPassword) {
      setError("The two passwords do not match.");
      return;
    }

    setPending(true);
    const supabase = createClient();
    const { data, error: signUpError } = await supabase.auth.signUp({
      email: email.trim(),
      password,
      options: {
        // The database trigger copies full_name into the new citizen profile.
        data: { full_name: fullName.trim() },
      },
    });
    setPending(false);

    if (signUpError) {
      setError("The account could not be created. Check the email and password, then try again.");
      return;
    }

    // Email confirmation is on when Supabase creates the user but does not return a session.
    if (!data.session) {
      setInfo("Check your email to confirm the account, then log in.");
      return;
    }

    router.push("/dashboard");
    router.refresh();
  }

  return (
    <form onSubmit={(event) => void onSubmit(event)} className="rounded-xl border border-zinc-200 bg-white p-6 shadow-sm">
      <h1 className="text-2xl font-semibold text-zinc-900">Sign up</h1>
      <label className="mt-4 block text-sm font-medium text-zinc-800" htmlFor="full-name">
        Full name
        <input
          id="full-name"
          type="text"
          autoComplete="name"
          value={fullName}
          onChange={(event) => setFullName(event.target.value)}
          className="mt-1 w-full rounded-md border border-zinc-300 px-3 py-2"
        />
      </label>
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
          autoComplete="new-password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          className="mt-1 w-full rounded-md border border-zinc-300 px-3 py-2"
        />
      </label>
      <label className="mt-4 block text-sm font-medium text-zinc-800" htmlFor="confirm-password">
        Confirm password
        <input
          id="confirm-password"
          type="password"
          autoComplete="new-password"
          value={confirmPassword}
          onChange={(event) => setConfirmPassword(event.target.value)}
          className="mt-1 w-full rounded-md border border-zinc-300 px-3 py-2"
        />
      </label>
      {error ? <p className="mt-4 text-sm text-red-600">{error}</p> : null}
      {info ? <p className="mt-4 text-sm text-zinc-700">{info}</p> : null}
      <button
        type="submit"
        disabled={pending}
        className="mt-6 rounded-md bg-zinc-900 px-4 py-2 text-sm text-white disabled:opacity-60"
      >
        {pending ? "Creating account..." : "Sign up"}
      </button>
    </form>
  );
}
