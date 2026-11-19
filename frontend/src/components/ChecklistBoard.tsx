"use client";

// The checklist the citizen sees. Uploads update the progress without reloading the page.

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { BackLink } from "@/components/BackLink";
import { Card } from "@/components/Card";
import { CheckList } from "@/components/CheckList";
import { Disclaimer } from "@/components/Disclaimer";
import { UploadSlot } from "@/components/UploadSlot";
import { adviceMatches, explainFailureMessage, issueSignature, type AiAdvice } from "@/lib/ai";
import { ApiError, NETWORK_ERROR, explainApplication, fetchAiAdvice, generateReport, validateApplication } from "@/lib/api";
import { reportFailureMessage } from "@/lib/report";
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
  serviceSlug = null,
}: {
  applicationId: string;
  title: string;
  statusLabel: string;
  slots: ChecklistSlot[];
  results: ValidationResult[];
  language?: Language;
  serviceSlug?: string | null;
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
  const [generating, setGenerating] = useState(false);
  const [reportError, setReportError] = useState<string | null>(null);
  const adviceSignature = useRef<string | null>(null);
  const epoch = useRef(0);
  const suspended = useRef<ValidationResult[] | null>(null);
  const gate = useRef({ running: false, again: false });
  const flight = useRef<Promise<void> | null>(null);
  const uploadedCount = slots.filter((slot) => uploads[slot.id]).length;
  const stillReading = Object.values(uploads).some(
    (upload) => upload && (upload.status === "uploaded" || upload.status === "processing"),
  );
  const canGenerate = uploadedCount > 0 && !stillReading && !generating;

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
  const passedChecks = checks.filter((result) => result.status === "pass");
  const failedChecks = checks.filter((result) => result.status === "fail");
  const warningChecks = checks.filter((result) => result.status === "warning");
  const explanations = Object.fromEntries((advice?.items ?? []).map((item) => [item.id, item.explanation]));
  const readinessLabel = checking
    ? "Checking your documents…"
    : checkError
      ? "Checks could not be updated"
      : checks.length === 0
        ? "Checks have not been run yet"
        : failedChecks.length > 0
          ? "Needs attention"
          : warningChecks.length > 0
            ? "Review warnings"
            : "Checks passed";

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
    if (explaining) {
      return;
    }
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
      setAdviceError(
        caught instanceof ApiError
          ? explainFailureMessage(caught.status, caught.message)
          : "AI assistance is unavailable right now – your standard checks still work",
      );
    } finally {
      setExplaining(false);
    }
  }

  async function generateReadinessReport() {
    if (generating) {
      return;
    }
    setGenerating(true);
    setReportError(null);
    try {
      const supabase = createClient();
      const { data } = await supabase.auth.getSession();
      const token = data.session?.access_token;
      if (!token) {
        router.push(`/login?next=/applications/${applicationId}`);
        return;
      }
      await generateReport(applicationId, token);
      router.push(`/applications/${applicationId}/report`);
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 401) {
        router.push(`/login?next=/applications/${applicationId}`);
        return;
      }
      setReportError(
        caught instanceof ApiError
          ? reportFailureMessage(caught.status, caught.message)
          : "The report could not be created. Please try again.",
      );
    } finally {
      setGenerating(false);
    }
  }

  return (
    <>
      <div className="flex flex-wrap gap-x-4 gap-y-2">
        <BackLink href="/applications">Back to My applications</BackLink>
        {serviceSlug ? (
          <BackLink href={`/services/${serviceSlug}`}>Back to required documents</BackLink>
        ) : null}
      </div>
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
      <div className="flex flex-col gap-4 lg:grid lg:grid-cols-[minmax(0,1.7fr)_minmax(20rem,24rem)] lg:items-start lg:gap-6">
        <ul className="order-2 flex flex-col gap-4 lg:order-1" data-required-count={slots.length}>
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
        <aside
          className="panel order-1 lg:order-2 lg:sticky lg:top-4"
          aria-labelledby="readiness-heading"
          aria-live="polite"
        >
          <h2 id="readiness-heading" className="text-lg font-semibold text-navy">
            Readiness and results
          </h2>
          <p className="mt-2 inline-flex w-fit rounded-full bg-sky px-3 py-1 text-sm font-medium text-navy">
            {readinessLabel}
          </p>
          {checks.length > 0 ? (
            <p className="mt-2 text-sm text-ink">
              {passedChecks.length} passed, {warningChecks.length} warning
              {warningChecks.length === 1 ? "" : "s"}, {failedChecks.length} need a fix
            </p>
          ) : null}
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
          {checks.length > 0 ? (
            <CheckList results={checks} explanations={explanations} />
          ) : (
            <p className="mt-2 text-sm text-muted">No checklist results yet. Upload a document or re-run checks.</p>
          )}
          {advice?.overall_tip ? (
            <div className="mt-3 rounded-lg border border-saffron bg-sky p-3">
              <p className="text-sm font-semibold text-navy">Overall tip</p>
              <p className="mt-1 text-sm text-ink">{advice.overall_tip}</p>
              <p className="mt-2 text-sm text-muted">
                AI-written advice – always confirm with the official e-Sevai portal
              </p>
            </div>
          ) : null}
          <div className="mt-4 flex flex-col gap-3">
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
              {explaining ? <p className="mt-2 text-sm text-ink">Writing a simple explanation…</p> : null}
              {adviceError ? <p className="mt-2 text-sm text-ink">{adviceError}</p> : null}
              {adviceError ? (
                <button type="button" className="btn-secondary mt-2" onClick={() => void explainIssues()}>
                  Retry
                </button>
              ) : null}
              {advice ? (
                <p className="mt-2 text-sm text-muted">
                  AI-written advice – always confirm with the official e-Sevai portal
                </p>
              ) : null}
            </div>
            <div>
              <button
                type="button"
                className="btn-primary w-full"
                disabled={!canGenerate}
                onClick={() => void generateReadinessReport()}
              >
                {generating ? "Generating…" : "Generate readiness report"}
              </button>
              {stillReading ? (
                <p className="mt-2 text-sm text-ink">Wait until every uploaded file has finished being read.</p>
              ) : null}
              {uploadedCount === 0 ? (
                <p className="mt-2 text-sm text-muted">Upload at least one document first.</p>
              ) : null}
              {reportError ? <p className="mt-2 text-sm text-red-800">{reportError}</p> : null}
              {reportError ? (
                <button type="button" className="btn-secondary mt-2" onClick={() => void generateReadinessReport()}>
                  Retry
                </button>
              ) : null}
            </div>
          </div>
        </aside>
      </div>
    </>
  );
}
