"use client";

import { useRouter } from "next/navigation";

export function ErrorMessage({ message }: { message: string }) {
  const router = useRouter();

  return (
    <div className="rounded-2xl border border-red-200 bg-red-50 p-5" role="alert">
      <h2 className="text-lg font-semibold text-red-900">Something went wrong</h2>
      <p className="mt-2 text-red-800">{message}</p>
      <button type="button" onClick={() => router.refresh()} className="btn-primary mt-4">
        Retry
      </button>
    </div>
  );
}
