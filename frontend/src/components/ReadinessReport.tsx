"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AlertCircle, CircleCheck, CircleX } from "lucide-react";

import { Disclaimer } from "@/components/Disclaimer";
import { explainFailureMessage, type AiAdvice } from "@/lib/ai";
import {
  ApiError,
  explainApplication,
  fetchAiAdvice,
  fetchReport,
  generateReport,
} from "@/lib/api";
import { parseLanguage, pickName, type Language } from "@/lib/language";
import { DOCUMENT_STATE_COPY, issueListKey, LABEL_COPY, reportFailureMessage } from "@/lib/report";
import { createClient } from "@/lib/supabase/client";
import type { ReadinessLabel, ReadinessReport as Report } from "@/lib/types";

const ICONS: Record<ReadinessLabel, typeof CircleCheck> = {
  ready: CircleCheck,
  almost_ready: AlertCircle,
  not_ready: CircleX,
};

function ScoreRing({ score, label }: { score: number; label: ReadinessLabel }) {
  const radius = 42;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (Math.max(0, Math.min(100, score)) / 100) * circumference;
  const copy = LABEL_COPY[label];
  const Icon = ICONS[label];
  return (
    <div className="print-card flex flex-col items-center gap-4 rounded-xl border border-line bg-white p-6 sm:flex-row sm:items-center">
      <div className="relative h-28 w-28 shrink-0" aria-hidden="true">
        <svg viewBox="0 0 100 100" className="h-28 w-28 -rotate-90">
          <circle cx="50" cy="50" r={radius} fill="none" stroke="#d2dde8" strokeWidth="10" />
          <circle
            cx="50"
            cy="50"
            r={radius}
            fill="none"
            stroke={label === "ready" ? "#0f6b3f" : label === "almost_ready" ? "#b8611a" : "#b91c1c"}
            strokeWidth="10"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            strokeLinecap="round"
          />
        </svg>
        <p className="absolute inset-0 grid place-items-center text-2xl font-semibold text-navy">{score}</p>
      </div>
      <div>
        <p className="text-sm font-medium text-muted">Readiness score</p>
        <p className={`mt-2 inline-flex items-center gap-2 rounded-full px-3 py-1 text-sm font-semibold ${copy.className}`}>
          <Icon aria-hidden="true" className="h-4 w-4" />
          {copy.title}
        </p>
        <p className="mt-2 text-sm text-ink">{copy.hint}</p>
        <p className="sr-only">
          Score {score} out of 100. {copy.title}. {copy.hint}
        </p>
      </div>
    </div>
  );
}

export function ReadinessReport({
  applicationId,
  serviceName,
  language,
}: {
  applicationId: string;
  serviceName: { name_en: string; name_ta: string | null };
  language: Language;
}) {
  const router = useRouter();
  const [report, setReport] = useState<Report | null>(null);
  const [current, setCurrent] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [generating, setGenerating] = useState(false);
  const [advice, setAdvice] = useState<AiAdvice | null>(null);
  const [explaining, setExplaining] = useState(false);
  const [adviceError, setAdviceError] = useState<string | null>(null);
  const title = pickName(serviceName, language);

  async function tokenOrLogin(): Promise<string | null> {
    const supabase = createClient();
    const { data } = await supabase.auth.getSession();
    const token = data.session?.access_token;
    if (!token) {
      router.push(`/login?next=/applications/${applicationId}/report`);
      return null;
    }
    return token;
  }

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const supabase = createClient();
        const { data } = await supabase.auth.getSession();
        const token = data.session?.access_token;
        if (!token) {
          router.push(`/login?next=/applications/${applicationId}/report`);
          return;
        }
        const payload = await fetchReport(applicationId, token);
        if (cancelled) {
          return;
        }
        setReport(payload.report);
        setCurrent(payload.is_current);
        if (payload.report) {
          try {
            const saved = await fetchAiAdvice(applicationId, token);
            if (!cancelled) {
              setAdvice(saved);
            }
          } catch {
            if (!cancelled) {
              setAdvice(null);
            }
          }
        }
      } catch (caught) {
        if (cancelled) {
          return;
        }
        if (caught instanceof ApiError && caught.status === 401) {
          router.push(`/login?next=/applications/${applicationId}/report`);
          return;
        }
        setError(caught instanceof Error ? caught.message : "The report could not be loaded.");
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [applicationId, router]);

  async function recheck() {
    setGenerating(true);
    setError(null);
    try {
      const token = await tokenOrLogin();
      if (!token) {
        return;
      }
      const next = await generateReport(applicationId, token);
      setReport(next);
      setCurrent(true);
      setAdvice(null);
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 401) {
        router.push(`/login?next=/applications/${applicationId}/report`);
        return;
      }
      setError(
        caught instanceof ApiError
          ? reportFailureMessage(caught.status, caught.message)
          : "The report could not be created. Please try again.",
      );
    } finally {
      setGenerating(false);
    }
  }

  async function explainIssues() {
    setExplaining(true);
    setAdviceError(null);
    try {
      const token = await tokenOrLogin();
      if (!token) {
        return;
      }
      const match = document.cookie.match(/(?:^|; )preferred_language=([^;]*)/);
      const chosen = parseLanguage(match ? decodeURIComponent(match[1]) : language);
      const next = await explainApplication(applicationId, token, chosen);
      setAdvice(next);
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 401) {
        router.push(`/login?next=/applications/${applicationId}/report`);
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

  const generated = report?.generated_at
    ? new Date(report.generated_at).toLocaleString(language === "ta" ? "ta-IN" : "en-IN")
    : "";
  const stale = !loading && (!report || !current);

  return (
    <div className="flex flex-col gap-4">
      <header className="page-banner flex flex-col gap-2">
        <p className="text-xs font-semibold tracking-[0.14em] text-royal uppercase">Readiness report</p>
        <h1 className="text-3xl font-semibold tracking-tight text-navy">{title}</h1>
        {generated ? <p className="text-sm text-ink">Generated {generated}</p> : null}
      </header>
      <Disclaimer />
      <div aria-live="polite">
        {loading ? <p className="text-sm text-ink">Loading your report…</p> : null}
        {error ? (
          <div className="rounded-md border border-red-200 bg-red-50 p-4 text-red-800">
            <p>{error}</p>
            <button type="button" className="btn-secondary mt-3 print:hidden" onClick={() => void recheck()}>
              Retry
            </button>
          </div>
        ) : null}
        {stale && !error ? (
          <div className="rounded-md border border-saffron/40 bg-[#fff8ef] p-4 text-[#5c3b12]">
            <p>Your documents changed after this report – generate it again</p>
            <button type="button" className="btn-primary mt-3 print:hidden" onClick={() => void recheck()} disabled={generating}>
              {generating ? "Generating…" : "Generate readiness report"}
            </button>
          </div>
        ) : null}
      </div>
      {report && current ? (
        <>
          <ScoreRing score={report.score} label={report.label} />
          <ul className="print-card grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            <li className="rounded-lg border border-line bg-white p-4">
              <p className="text-sm text-muted">Documents uploaded</p>
              <p className="mt-1 text-xl font-semibold text-navy">
                {report.counts.documents_uploaded} of {report.counts.documents_required}
              </p>
            </li>
            <li className="rounded-lg border border-line bg-white p-4">
              <p className="text-sm text-muted">Missing mandatory</p>
              <p className="mt-1 text-xl font-semibold text-navy">{report.counts.mandatory_missing}</p>
            </li>
            <li className="rounded-lg border border-line bg-white p-4">
              <p className="text-sm text-muted">Passed / warnings / needs fix</p>
              <p className="mt-1 text-xl font-semibold text-navy">
                {report.counts.pass} / {report.counts.warning} / {report.counts.fail}
              </p>
            </li>
          </ul>
          <section className="print-card rounded-xl border border-line bg-white p-5" aria-labelledby="next-steps-heading">
            <h2 id="next-steps-heading" className="text-lg font-semibold text-navy">
              What to do next
            </h2>
            <ol className="mt-3 flex flex-col gap-2">
              {report.next_steps.map((step) => (
                <li key={`${step.priority}-${step.text}`} className="flex gap-3 text-sm text-ink">
                  <span
                    className="mt-0.5 inline-block h-5 w-5 shrink-0 rounded-sm border border-navy"
                    aria-hidden="true"
                  />
                  <span>
                    <span className="font-semibold">{step.priority}.</span> {step.text}
                  </span>
                </li>
              ))}
            </ol>
          </section>
          <section className="flex flex-col gap-3" aria-labelledby="documents-heading">
            <h2 id="documents-heading" className="text-lg font-semibold text-navy">
              Your documents
            </h2>
            {report.documents.map((document) => {
              const state = DOCUMENT_STATE_COPY[document.state];
              return (
                <article key={document.required_document_id} className="print-card rounded-xl border border-line bg-white p-5">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <h3 className="text-base font-semibold text-navy">{pickName(document, language)}</h3>
                    <p className={`inline-flex rounded-full px-3 py-1 text-sm font-semibold ${state.className}`}>
                      {state.title}
                      {document.score != null ? ` · ${document.score}` : ""}
                    </p>
                  </div>
                  {document.issues.length === 0 ? (
                    <p className="mt-2 text-sm text-muted">No issues to fix on this document.</p>
                  ) : (
                    <ul className="mt-3 flex flex-col gap-2">
                      {document.issues.map((issue, index) => (
                        <li key={issueListKey(`${document.code}-${issue.check_code}`, index)} className="text-sm text-ink">
                          <p>{issue.message}</p>
                          {issue.fix_suggestion ? (
                            <p className="mt-1 text-muted">What to do: {issue.fix_suggestion}</p>
                          ) : null}
                        </li>
                      ))}
                    </ul>
                  )}
                </article>
              );
            })}
          </section>
          {report.application_issues.length > 0 ? (
            <section className="print-card rounded-xl border border-line bg-white p-5" aria-labelledby="between-heading">
              <h2 id="between-heading" className="text-lg font-semibold text-navy">
                Between your documents
              </h2>
              <ul className="mt-3 flex flex-col gap-2">
                {report.application_issues.map((issue, index) => (
                  <li key={issueListKey(issue.check_code, index)} className="text-sm text-ink">
                    <p>{issue.message}</p>
                    {issue.fix_suggestion ? <p className="mt-1 text-muted">What to do: {issue.fix_suggestion}</p> : null}
                  </li>
                ))}
              </ul>
            </section>
          ) : null}
          <section className="print-card rounded-xl border border-line bg-white p-5" aria-labelledby="carry-heading">
            <h2 id="carry-heading" className="text-lg font-semibold text-navy">
              Documents to carry
            </h2>
            <ul className="mt-3 flex flex-col gap-2">
              {report.carry_list.map((item, index) => (
                <li key={`${item.name_en}-${index}`} className="flex flex-wrap items-center justify-between gap-2 text-sm text-ink">
                  <span>{pickName(item, language)}</span>
                  <span className="rounded-full bg-sky px-3 py-1 font-medium text-navy">
                    {item.is_mandatory ? "Mandatory" : "Optional"}
                  </span>
                </li>
              ))}
            </ul>
          </section>
          {advice ? (
            <section className="print-card rounded-xl border border-saffron bg-sky p-5 print:hidden">
              <h2 className="text-lg font-semibold text-navy">AI-written advice</h2>
              {advice.overall_tip ? <p className="mt-2 text-sm text-ink">{advice.overall_tip}</p> : null}
              <ul className="mt-3 flex flex-col gap-2">
                {advice.items.map((item) => (
                  <li key={item.id} className="text-sm text-ink">
                    {item.explanation}
                  </li>
                ))}
              </ul>
              <p className="mt-2 text-sm text-muted">AI-written advice – always confirm with the official e-Sevai portal</p>
            </section>
          ) : null}
          <p className="hidden text-xs text-muted print:block">
            Generated by e-Sevai Pre-Flight – independent pre-check, not an official result
          </p>
        </>
      ) : null}
      <div className="flex flex-col gap-3 print:hidden sm:flex-row sm:flex-wrap">
        <Link href={`/applications/${applicationId}`} className="btn-secondary">
          Back to checklist
        </Link>
        <button type="button" className="btn-primary" onClick={() => void recheck()} disabled={generating}>
          {generating ? "Checking…" : "Re-check"}
        </button>
        <button
          type="button"
          className="btn-secondary"
          onClick={() => void explainIssues()}
          disabled={explaining || !report || !current}
        >
          {explaining ? "Writing a simple explanation…" : "Explain issues in simple words"}
        </button>
        <button type="button" className="btn-secondary" onClick={() => window.print()}>
          Print / Save as PDF
        </button>
      </div>
      {adviceError ? (
        <div className="print:hidden">
          <p className="text-sm text-ink">{adviceError}</p>
          <button type="button" className="btn-secondary mt-2" onClick={() => void explainIssues()}>
            Retry
          </button>
        </div>
      ) : null}
    </div>
  );
}
