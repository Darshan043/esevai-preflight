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
      className="btn-secondary border-red-200 text-red-800 hover:bg-red-50"
    >
      {pending ? "Deleting..." : "Delete"}
    </button>
  );
}
