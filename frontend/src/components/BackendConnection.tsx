"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { ApiError, fetchWithToken, type MeResponse } from "@/lib/api";
import { createClient } from "@/lib/supabase/client";

export function BackendConnection() {
  const router = useRouter();
  const [me, setMe] = useState<MeResponse | null>(null);
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
          setMe(null);
          setError("Your session has no access token. Sign in again.");
          setLoading(false);
        }
        return;
      }

      try {
        const result = await fetchWithToken<MeResponse>("/me", token);
        if (cancelled) {
          return;
        }
        setMe(result);
        setError(null);
      } catch (caught: unknown) {
        if (cancelled) {
          return;
        }
        if (caught instanceof ApiError && caught.status === 401) {
          router.push("/login");
          return;
        }
        setMe(null);
        setError(caught instanceof Error ? caught.message : "The backend could not be reached.");
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
      <h2 className="text-xl font-semibold text-navy">Backend connection</h2>
      {loading ? <p className="mt-4 text-muted">Checking the signed-in API...</p> : null}
      {!loading && error ? (
        <div className="mt-4">
          <p className="text-red-600">{error}</p>
          <button
            type="button"
            onClick={() => {
              setLoading(true);
              setError(null);
              setMe(null);
              setAttempt((current) => current + 1);
            }}
            className="btn-primary mt-3"
          >
            Retry
          </button>
        </div>
      ) : null}
      {!loading && me ? (
        <dl className="mt-4 space-y-2 text-sm text-ink">
          <div>
            <dt className="inline font-medium">Result: </dt>
            <dd className="inline">Success</dd>
          </div>
          <div>
            <dt className="inline font-medium">User id: </dt>
            <dd className="inline break-all">{me.user_id}</dd>
          </div>
          <div>
            <dt className="inline font-medium">Email: </dt>
            <dd className="inline">{me.email ?? "Not provided"}</dd>
          </div>
          <div>
            <dt className="inline font-medium">Role: </dt>
            <dd className="inline">{me.role}</dd>
          </div>
        </dl>
      ) : null}
    </section>
  );
}
