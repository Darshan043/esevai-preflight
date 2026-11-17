"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { ApiError, fetchWithToken, type AdminPingResponse } from "@/lib/api";
import { createClient } from "@/lib/supabase/client";

export function AdminPing() {
  const router = useRouter();
  const [result, setResult] = useState<AdminPingResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      const supabase = createClient();
      const { data } = await supabase.auth.getSession();
      const token = data.session?.access_token;
      if (!token) {
        if (!cancelled) {
          setError("Your session has no access token. Sign in again.");
          setLoading(false);
        }
        return;
      }

      try {
        const body = await fetchWithToken<AdminPingResponse>("/admin/ping", token);
        if (cancelled) {
          return;
        }
        setResult(body);
        setError(null);
      } catch (caught: unknown) {
        if (cancelled) {
          return;
        }
        if (caught instanceof ApiError && caught.status === 401) {
          router.push("/login");
          return;
        }
        setResult(null);
        setError(caught instanceof Error ? caught.message : "The admin check failed.");
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, [attempt, router]);

  return (
    <section className="panel">
      <h2 className="text-xl font-semibold text-navy">Admin check</h2>
      {loading ? <p className="mt-4 text-muted">Checking admin access...</p> : null}
      {!loading && error ? (
        <div className="mt-4">
          <p className="text-red-600">{error}</p>
          <button
            type="button"
            onClick={() => {
              setLoading(true);
              setError(null);
              setResult(null);
              setAttempt((current) => current + 1);
            }}
            className="btn-primary mt-3"
          >
            Retry
          </button>
        </div>
      ) : null}
      {!loading && result ? <p className="mt-4 text-ink">{result.message}</p> : null}
    </section>
  );
}
