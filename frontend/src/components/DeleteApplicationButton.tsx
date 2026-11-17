"use client";

import { useState } from "react";

import { deleteApplication } from "@/app/applications/actions";

export function DeleteApplicationButton({ applicationId }: { applicationId: string }) {
  const [pending, setPending] = useState(false);

  return (
    <button
      type="button"
      disabled={pending}
      onClick={() => {
        const confirmed = window.confirm("Delete this application? This cannot be undone.");
        if (!confirmed) {
          return;
        }
        setPending(true);
        void deleteApplication(applicationId);
      }}
      className="inline-flex min-h-11 items-center rounded-md border border-red-300 px-4 text-sm font-medium text-red-800 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-zinc-900 disabled:opacity-60"
    >
      {pending ? "Deleting..." : "Delete"}
    </button>
  );
}
