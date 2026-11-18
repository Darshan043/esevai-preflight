import type { ReadinessLabel } from "@/lib/types";

export const LABEL_COPY: Record<
  ReadinessLabel,
  { title: string; hint: string; className: string }
> = {
  ready: {
    title: "Ready to apply",
    hint: "Your documents look complete enough to take to the e-Sevai centre.",
    className: "bg-green-100 text-green-800",
  },
  almost_ready: {
    title: "Almost ready",
    hint: "A few items still need a check before you apply.",
    className: "bg-amber-100 text-amber-800",
  },
  not_ready: {
    title: "Not ready yet",
    hint: "Fix the items below before you apply.",
    className: "bg-red-100 text-red-800",
  },
};

export const DOCUMENT_STATE_COPY: Record<
  "missing" | "passed" | "check_advised" | "needs_fix",
  { title: string; className: string }
> = {
  missing: { title: "Missing", className: "bg-zinc-100 text-zinc-700" },
  passed: { title: "Passed", className: "bg-green-100 text-green-800" },
  check_advised: { title: "Check advised", className: "bg-amber-100 text-amber-800" },
  needs_fix: { title: "Needs fix", className: "bg-red-100 text-red-800" },
};

export function isReadinessLabel(value: unknown): value is ReadinessLabel {
  return value === "ready" || value === "almost_ready" || value === "not_ready";
}

export function issueListKey(checkCode: string, index: number): string {
  return `${checkCode}-${index}`;
}

export function reportFailureMessage(status: number, detail: string): string {
  if (status === 400) {
    return detail || "Upload at least one document first.";
  }
  if (status === 409) {
    return detail || "Some documents are still being read. Wait a moment and try again.";
  }
  return detail || "The report could not be created. Please try again.";
}
