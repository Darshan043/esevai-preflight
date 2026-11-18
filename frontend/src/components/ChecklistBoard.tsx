"use client";

// The checklist the citizen sees. Uploads update the progress without reloading the page.

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { Card } from "@/components/Card";
import { CheckList } from "@/components/CheckList";
import { Disclaimer } from "@/components/Disclaimer";
import { UploadSlot } from "@/components/UploadSlot";
import { adviceMatches, issueSignature, type AiAdvice } from "@/lib/ai";
import { ApiError, NETWORK_ERROR, explainApplication, fetchAiAdvice, validateApplication } from "@/lib/api";
import { parseLanguage, type Language } from "@/lib/language";
import { restoreSuspended, resultsAfterLocalChange, validationOutcome } from "@/lib/replacement";
import { createClient } from "@/lib/supabase/client";
import type { PublicUpload, ValidationResult } from "@/lib/types";

export type ChecklistSlot = {
  id: string;
  name: string;
  description: string | null;
  isMandatory: boolean;
  acceptedFormats: string[];
  maxSizeMb: number;
  validity: string | null;
  upload: PublicUpload | null;
};

export function ChecklistBoard({
  applicationId,
  title,
  statusLabel,
  slots,
  results,
  language = "en",
}: {
  applicationId: string;
  title: string;
  statusLabel: string;
  slots: ChecklistSlot[];
  results: ValidationResult[];
  language?: Language;
}) {
  const router = useRouter();
  const [uploads, setUploads] = useState<Record<string, PublicUpload | null>>(() => {
    const initial: Record<string, PublicUpload | null> = {};
    for (const slot of slots) {
      initial[slot.id] = slot.upload;
    }
    return initial;
  });
  const [checks, setChecks] = useState<ValidationResult[]>(results);
  const [checkError, setCheckError] = useState<string | null>(null);
  const [checking, setChecking] = useState(false);
  const [checkNote, setCheckNote] = useState<string | null>(null);
  const [advice, setAdvice] = useState<AiAdvice | null>(null);
  const [adviceError, setAdviceError] = useState<string | null>(null);
  const [explaining, setExplaining] = useState(false);
  const adviceSignature = useRef<string | null>(null);
  const epoch = useRef(0);
  const suspended = useRef<ValidationResult[] | null>(null);
  const gate = useRef({ running: false, again: false });
  const flight = useRef<Promise<void> | null>(null);
  const shared = checks.filter((result) => !result.uploaded_document_id);
  const uploadedCount = slots.filter((slot) => uploads[slot.id]).length;

  function suspend(uploadId: string | null) {
    epoch.current += 1;
    setChecks((current) => {
      const kept = resultsAfterLocalChange(current, uploadId);
      const keptIds = new Set(kept.map((result) => result.id));
      suspended.current = current.filter((result) => !keptIds.has(result.id));
      return kept;
    });
    setCheckNote(null);
  }

  function undoSuspend() {
    const putBack = suspended.current;
    suspended.current = null;
    if (!putBack?.length) {
      return;
    }
    setChecks((current) => restoreSuspended(current, putBack));
  }

  function refreshChecks(): Promise<void> {
    gate.current.again = true;
    if (gate.current.running) {
      return flight.current ?? Promise.resolve();
    }
    gate.current.running = true;
    const promise = (async () => {
      try {
        while (gate.current.again) {
          gate.current.again = false;
          const started = epoch.current;
          setChecking(true);
          setCheckError(null);
          try {
            const supabase = createClient();
            const { data } = await supabase.auth.getSession();
            const token = data.session?.access_token;
            if (!token) {
              gate.current.again = false;
              router.push(`/login?next=/applications/${applicationId}`);
              return;
            }
            const payload = await validateApplication(applicationId, token);
            const outcome = validationOutcome(started, epoch.current, gate.current.again);
            gate.current.again = outcome.repeat;
            if (outcome.apply) {
              setChecks(payload.results);
              const nextSignature = issueSignature(payload.results);
              if (adviceSignature.current !== nextSignature) {
                setAdvice(null);
                adviceSignature.current = null;
              }
              suspended.current = null;
              setCheckNote("Checks updated.");
            }
          } catch (caught) {
            const outcome = validationOutcome(started, epoch.current, gate.current.again);
            gate.current.again = outcome.repeat;
            if (!outcome.apply) {
              continue;
            }
            if (caught instanceof ApiError && caught.status === 401) {
              gate.current.again = false;
              router.push(`/login?next=/applications/${applicationId}`);
              return;
            }
            setCheckError(caught instanceof Error ? caught.message : NETWORK_ERROR);
          } finally {
            if (started === epoch.current && !gate.current.again) {
              setChecking(false);
            }
          }
        }
      } finally {
        gate.current.running = false;
        if (gate.current.again) {
          void refreshChecks();
        }
      }
    })();
    flight.current = promise;
    return promise;
  }
  const progress = slots.length === 0 ? 0 : Math.round((uploadedCount / slots.length) * 100);
  const problems = checks.filter((result) => result.status !== "pass");
  const explanations = Object.fromEntries((advice?.items ?? []).map((item) => [item.id, item.explanation]));

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      const supabase = createClient();
      const { data } = await supabase.auth.getSession();
      const token = data.session?.access_token;
      if (!token) {
        return;
      }
      try {
        const saved = await fetchAiAdvice(applicationId, token);
        if (cancelled || !adviceMatches(saved, results)) {
          return;
        }
        setAdvice(saved);
        adviceSignature.current = issueSignature(results);
      } catch {
        // Saved advice is optional. The checklist still works without it.
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [applicationId, results]);

  async function explainIssues() {
    setExplaining(true);
    setAdviceError(null);
    try {
      const supabase = createClient();
      const { data } = await supabase.auth.getSession();
      const token = data.session?.access_token;
      if (!token) {
        router.push(`/login?next=/applications/${applicationId}`);
        return;
      }
      const match = document.cookie.match(/(?:^|; )preferred_language=([^;]*)/);
      const chosen = parseLanguage(match ? decodeURIComponent(match[1]) : language);
      const next = await explainApplication(applicationId, token, chosen);
      if (!adviceMatches(next, checks)) {
        setAdvice(null);
        adviceSignature.current = null;
        return;
      }
      setAdvice(next);
      adviceSignature.current = issueSignature(checks);
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 401) {
        router.push(`/login?next=/applications/${applicationId}`);
        return;
      }
      if (caught instanceof ApiError && caught.status === 429) {
        setAdviceError("The daily AI limit has been reached. Please try again tomorrow.");
        return;
      }
      if (caught instanceof ApiError && caught.message === "AI assistance is turned off.") {
        setAdviceError("AI assistance is turned off.");
        return;
      }
      setAdviceError(
        caught instanceof ApiError
          ? caught.message
          : "AI assistance is unavailable right now – your standard checks still work",
      );
    } finally {
      setExplaining(false);
    }
  }

  return (
    <>
      <header className="page-banner flex flex-col gap-3">
        <p className="text-xs font-semibold tracking-[0.14em] text-royal uppercase">Document checklist</p>
        <h1 className="text-3xl font-semibold tracking-tight text-navy">{title}</h1>
        <p className="inline-flex w-fit rounded-full bg-sky px-3 py-1 text-sm font-medium text-navy">{statusLabel}</p>
        <div>
          <p className="text-sm font-medium text-ink" id="upload-progress-label">
            {uploadedCount} of {slots.length} required documents uploaded
          </p>
          <div
            className="mt-2 h-3 overflow-hidden rounded-full bg-sky"
            role="progressbar"
            aria-labelledby="upload-progress-label"
            aria-valuemin={0}
            aria-valuemax={slots.length}
            aria-valuenow={uploadedCount}
          >
            <div className="h-full bg-royal" style={{ width: `${progress}%` }} />
          </div>
        </div>
      </header>
      <Disclaimer />
      <section className="panel" aria-live="polite">
        <h2 className="text-lg font-semibold text-navy">Checklist checks</h2>
        {checking ? <p className="mt-2 text-sm text-ink">Checking your documents…</p> : null}
        {checkNote ? <p className="mt-2 text-sm text-ink">{checkNote}</p> : null}
        {checkError ? (
          <div className="mt-2">
            <p className="text-sm text-red-800">{checkError}</p>
            <button type="button" className="btn-secondary mt-2" onClick={() => void refreshChecks()}>
              Retry
            </button>
          </div>
        ) : null}
        {shared.length > 0 ? (
          <CheckList results={shared} explanations={explanations} />
        ) : (
          <p className="mt-2 text-sm text-muted">No checklist-wide problems yet.</p>
        )}
        {advice?.overall_tip ? (
          <div className="mt-3 rounded-lg border border-saffron bg-sky p-3">
            <p className="text-sm font-semibold text-navy">Overall tip</p>
            <p className="mt-1 text-sm text-ink">{advice.overall_tip}</p>
            <p className="mt-2 text-sm text-muted">AI-written advice – always confirm with the official e-Sevai portal</p>
          </div>
        ) : null}
      </section>
      <ul className="flex flex-col gap-4" data-required-count={slots.length}>
        {slots.map((slot, index) => (
          <li key={slot.id}>
            <Card className="service-card">
              <h2 className="text-xl font-semibold text-navy">
                <span className="mr-2 text-sm font-semibold text-royal">{index + 1}.</span>
                {slot.name}
              </h2>
              <p className="mt-2 text-sm font-medium text-ink">{slot.isMandatory ? "Mandatory" : "Optional"}</p>
              {slot.description ? <p className="mt-2 text-muted">Tip: {slot.description}</p> : null}
              <p className="mt-2 text-sm text-ink">Accepted formats: {slot.acceptedFormats.join(", ")}</p>
              <p className="mt-1 text-sm text-ink">Maximum size: {slot.maxSizeMb} MB</p>
              {slot.validity ? <p className="mt-1 text-sm text-ink">{slot.validity}</p> : null}
              <UploadSlot
                applicationId={applicationId}
                document={slot}
                upload={uploads[slot.id] ?? null}
                results={checks}
                onActivity={() => refreshChecks()}
                onSuspend={() => suspend(uploads[slot.id]?.id ?? null)}
                onUndoSuspend={undoSuspend}
                explanations={explanations}
                onChange={(next) => {
                  setUploads((current) => ({ ...current, [slot.id]: next }));
                }}
              />
            </Card>
          </li>
        ))}
      </ul>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <button type="button" className="btn-primary" onClick={() => void refreshChecks()} disabled={checking}>
          {checking ? "Checking…" : "Re-run checks"}
        </button>
        <div>
          <button
            type="button"
            className="btn-secondary"
            onClick={() => void explainIssues()}
            disabled={explaining || problems.length === 0}
          >
            {explaining ? "Writing a simple explanation…" : "Explain issues in simple words"}
          </button>
          {adviceError ? <p className="mt-2 text-sm text-ink">{adviceError}</p> : null}
          {adviceError ? (
            <button type="button" className="btn-secondary mt-2" onClick={() => void explainIssues()}>
              Retry
            </button>
          ) : null}
          {advice ? (
            <p className="mt-2 text-sm text-muted">AI-written advice – always confirm with the official e-Sevai portal</p>
          ) : null}
        </div>
        <div>
          <button
            type="button"
            disabled
            className="inline-flex min-h-11 cursor-not-allowed items-center rounded-lg bg-line px-4 text-sm font-semibold text-muted"
          >
            Run readiness check
          </button>
          <p className="mt-2 text-sm text-muted">Report available in a later step</p>
        </div>
      </div>
    </>
  );
}
