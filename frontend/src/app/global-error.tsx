"use client";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  void error;
  return (
    <html lang="en">
      <body className="bg-[#f2f5f8] text-[#1c2836]">
        <main className="mx-auto max-w-3xl px-4 py-16">
          <h1 className="text-2xl font-semibold">This page could not be shown</h1>
          <p className="mt-2">Please try again. Your files and checks are still saved.</p>
          <button type="button" className="mt-4 rounded-md bg-[#0f4c81] px-4 py-2 text-white" onClick={() => reset()}>
            Try again
          </button>
        </main>
      </body>
    </html>
  );
}
