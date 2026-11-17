"use client";

import { useEffect, useState } from "react";

import { getHealth, type HealthResponse } from "@/lib/api";

export function SystemStatus() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  // Changing this number asks the effect to fetch again.
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let cancelled = false;

    getHealth()
      .then((result) => {
        if (cancelled) {
          return;
        }
        setHealth(result);
        setError(null);
      })
      .catch((caught: unknown) => {
        if (cancelled) {
          return;
        }
        setHealth(null);
        setError(caught instanceof Error ? caught.message : "The backend is not reachable.");
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [attempt]);

  const connected = health?.status === "ok";

  return (
    <section
      id="system-status"
      aria-label="System status"
      className="panel"
    >
      <h2 className="text-xl font-semibold text-navy">System status</h2>

      {loading ? <p className="mt-4 text-muted">Checking the backend...</p> : null}

      {!loading && error ? (
        <div className="mt-4">
          <p className="text-red-600">{error}</p>
          <button
            type="button"
            onClick={() => {
              setLoading(true);
              setError(null);
              setHealth(null);
              setAttempt((current) => current + 1);
            }}
            className="btn-primary mt-3"
          >
            Retry
          </button>
        </div>
      ) : null}

      {!loading && health ? (
        <dl className="mt-4 space-y-2 text-sm text-ink">
          <div>
            <dt className="inline font-medium">Backend status: </dt>
            <dd className="inline">{connected ? "Connected" : "Not reachable"}</dd>
          </div>
          <div>
            <dt className="inline font-medium">Service: </dt>
            <dd className="inline">{health.service}</dd>
          </div>
          <div>
            <dt className="inline font-medium">Version: </dt>
            <dd className="inline">{health.version}</dd>
          </div>
          <div>
            <dt className="inline font-medium">Environment: </dt>
            <dd className="inline">{health.environment}</dd>
          </div>
          <div>
            <dt className="inline font-medium">Time: </dt>
            <dd className="inline">{health.time}</dd>
          </div>
        </dl>
      ) : null}
    </section>
  );
}
