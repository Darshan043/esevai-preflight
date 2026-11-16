import { Suspense } from "react";

import { LoginForm } from "@/app/login/login-form";

export default function LoginPage() {
  return (
    <main className="mx-auto flex w-full max-w-md flex-col px-6 py-12">
      <Suspense fallback={<p className="text-zinc-600">Loading the login form...</p>}>
        <LoginForm />
      </Suspense>
    </main>
  );
}
