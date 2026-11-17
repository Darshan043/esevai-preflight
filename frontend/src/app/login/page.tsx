import { Suspense } from "react";

import { LoginForm } from "@/app/login/login-form";

export default function LoginPage() {
  return (
    <main className="page-wrap max-w-5xl">
      <div className="grid items-start gap-6 lg:grid-cols-[0.85fr_1.15fr]">
        <aside className="panel-ink">
          <p className="text-xs font-semibold tracking-[0.14em] text-sky uppercase">Account access</p>
          <h2 className="mt-2 text-2xl font-semibold">Sign in to continue a document check</h2>
          <ul className="mt-4 space-y-2 text-sm leading-6 text-sky">
            <li>Use the email and password for this assistant.</li>
            <li>Citizen accounts cannot open the admin area.</li>
            <li>This login is not a government portal login.</li>
          </ul>
        </aside>
        <Suspense fallback={<p className="text-muted">Loading the login form...</p>}>
          <LoginForm />
        </Suspense>
      </div>
    </main>
  );
}
