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
    if (pending) {
      return;
    }
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
      setInfo(
        "Account created. Open the confirmation link in your email before you log in. Login will not accept this password until that link is opened.",
      );
      return;
    }

    router.push("/dashboard");
    router.refresh();
  }

  return (
    <form onSubmit={(event) => void onSubmit(event)} className="panel">
      <p className="text-sm font-semibold text-royal">Account</p>
      <h1 className="mt-1 text-2xl font-semibold text-navy">Sign up</h1>
      <p className="mt-2 text-sm text-muted">Create a citizen account. New accounts are not admin accounts.</p>
      <label className="mt-4 block text-sm font-medium text-navy" htmlFor="full-name">
        Full name
        <input
          id="full-name"
          type="text"
          autoComplete="name"
          value={fullName}
          onChange={(event) => setFullName(event.target.value)}
          className="field"
        />
      </label>
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
          autoComplete="new-password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          className="field"
        />
      </label>
      <label className="mt-4 block text-sm font-medium text-navy" htmlFor="confirm-password">
        Confirm password
        <input
          id="confirm-password"
          type="password"
          autoComplete="new-password"
          value={confirmPassword}
          onChange={(event) => setConfirmPassword(event.target.value)}
          className="field"
        />
      </label>
      {error ? <p className="mt-4 text-sm text-red-700">{error}</p> : null}
      {info ? <p className="mt-4 text-sm text-ink">{info}</p> : null}
      <button type="submit" disabled={pending} className="btn-primary mt-6 w-full">
        {pending ? "Creating account..." : "Sign up"}
      </button>
    </form>
  );
}
