"use client";

import { AlertTriangle, CircleCheck, CircleX } from "lucide-react";

import type { ValidationResult } from "@/lib/types";

const labels = {
  pass: "Passed",
  warning: "Warning",
  fail: "Needs fix",
} as const;

function CheckIcon({ status }: { status: ValidationResult["status"] }) {
  if (status === "pass") {
    return <CircleCheck aria-hidden="true" className="h-4 w-4 text-green-700" />;
  }
  if (status === "warning") {
    return <AlertTriangle aria-hidden="true" className="h-4 w-4 text-amber-700" />;
  }
  return <CircleX aria-hidden="true" className="h-4 w-4 text-red-700" />;
}

function CheckRow({ result }: { result: ValidationResult }) {
  return (
    <li className="rounded-md border border-line bg-white p-3">
      <p className="flex items-center gap-2 text-sm font-semibold text-navy">
        <CheckIcon status={result.status} />
        {labels[result.status]}
      </p>
      <p className="mt-1 text-sm text-ink">{result.message}</p>
      {result.status !== "pass" && result.fix_suggestion ? (
        <p className="mt-1 text-sm text-muted">What to do: {result.fix_suggestion}</p>
      ) : null}
    </li>
  );
}

export function CheckList({ results }: { results: ValidationResult[] }) {
  if (results.length === 0) {
    return null;
  }
  const problems = results.filter((result) => result.status !== "pass");
  const passed = results.filter((result) => result.status === "pass");

  return (
    <div className="mt-4">
      <h3 className="text-sm font-semibold text-navy">Checks</h3>
      <ul className="mt-2 flex flex-col gap-2">
        {problems.map((result) => (
          <CheckRow key={result.id || `${result.check_code}-${result.message}`} result={result} />
        ))}
      </ul>
      {passed.length > 0 ? (
        <details className="mt-2">
          <summary className="min-h-11 cursor-pointer text-sm font-medium text-royal">
            Show passed checks ({passed.length})
          </summary>
          <ul className="mt-2 flex flex-col gap-2">
            {passed.map((result) => (
              <CheckRow key={result.id || `${result.check_code}-pass`} result={result} />
            ))}
          </ul>
        </details>
      ) : null}
    </div>
  );
}
