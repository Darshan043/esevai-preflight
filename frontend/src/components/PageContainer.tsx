// Centers page content and keeps type large enough to read on a phone.

export function PageContainer({ children }: { children: React.ReactNode }) {
  return (
    <main className="mx-auto flex w-full max-w-5xl flex-col gap-8 bg-white px-4 py-8 text-base text-zinc-900 sm:px-6">
      {children}
    </main>
  );
}
