"use client";

import { useEffect } from "react";

export default function ErrorPage({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error.name);
  }, [error]);

  return (
    <main className="page-wrap max-w-3xl">
      <section className="page-banner">
        <p className="text-xs font-semibold tracking-[0.14em] text-royal uppercase">Something went wrong</p>
        <h1 className="mt-1 text-2xl font-semibold text-navy">This page could not be shown</h1>
        <p className="mt-2 text-muted">Please try again. Your files and checks are still saved.</p>
        <button type="button" className="btn-primary mt-4 w-fit" onClick={() => reset()}>
          Try again
        </button>
      </section>
    </main>
  );
}
