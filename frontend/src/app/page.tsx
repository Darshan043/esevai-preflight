import { SystemStatus } from "@/components/SystemStatus";

export default function Home() {
  return (
    <main className="mx-auto flex w-full max-w-2xl flex-col gap-8 px-6 py-16">
      <header>
        <h1 className="text-3xl font-semibold tracking-tight text-zinc-900">e-Sevai Pre-Flight</h1>
        <p className="mt-2 text-lg text-zinc-600">Check your documents before you apply</p>
      </header>
      <SystemStatus />
    </main>
  );
}
