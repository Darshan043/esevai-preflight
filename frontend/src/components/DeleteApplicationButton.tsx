"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { ApiError, NETWORK_ERROR, deleteApplicationOnServer } from "@/lib/api";
import { createClient } from "@/lib/supabase/client";

export function DeleteApplicationButton({ applicationId }: { applicationId: string }) {
  const router = useRouter();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  return (
    <div className="flex flex-col items-start gap-2">
      <button
        type="button"
        disabled={pending}
        onClick={() => {
          const confirmed = window.confirm("Delete this application? This cannot be undone.");
          if (!confirmed) {
            return;
          }
          setPending(true);
          setError(null);
          void (async () => {
            try {
              const supabase = createClient();
              const { data } = await supabase.auth.getSession();
              const token = data.session?.access_token;
              if (!token) {
                router.push("/login?next=/applications");
                return;
              }
              await deleteApplicationOnServer(applicationId, token);
              router.refresh();
            } catch (caught) {
              if (caught instanceof ApiError && caught.status === 401) {
                router.push("/login?next=/applications");
                return;
              }
              setError(caught instanceof Error ? caught.message : NETWORK_ERROR);
            } finally {
              setPending(false);
            }
          })();
        }}
        className="btn-secondary border-red-200 text-red-800 hover:bg-red-50"
      >
        {pending ? "Deleting..." : "Delete"}
      </button>
      {error ? (
        <p className="text-sm text-red-800" role="alert">
          {error}
        </p>
      ) : null}
    </div>
  );
}
