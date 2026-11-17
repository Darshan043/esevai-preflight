"use client";

import { useRouter } from "next/navigation";

export function ErrorMessage({ message }: { message: string }) {
  const router = useRouter();

  return (
    <div className="rounded-xl border border-red-200 bg-red-50 p-5" role="alert">
      <h2 className="text-lg font-semibold text-red-900">Something went wrong</h2>
      <p className="mt-2 text-red-800">{message}</p>
      <button
        type="button"
        onClick={() => router.refresh()}
        className="mt-4 inline-flex min-h-11 items-center rounded-md bg-zinc-900 px-4 text-sm font-medium text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-zinc-900"
      >
        Retry
      </button>
    </div>
  );
}
