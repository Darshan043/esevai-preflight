import { SignupForm } from "@/app/signup/signup-form";

export default function SignupPage() {
  return (
    <main className="page-wrap max-w-5xl">
      <div className="grid items-start gap-6 lg:grid-cols-[0.85fr_1.15fr]">
        <aside className="panel-ink">
          <p className="text-xs font-semibold tracking-[0.14em] text-sky uppercase">New citizen account</p>
          <h2 className="mt-2 text-2xl font-semibold">Create an account for this assistant</h2>
          <ul className="mt-4 space-y-2 text-sm leading-6 text-sky">
            <li>New accounts are citizen accounts, not admin accounts.</li>
            <li>Your name is stored on your profile.</li>
            <li>This is not an official government registration.</li>
          </ul>
        </aside>
        <SignupForm />
      </div>
    </main>
  );
}
