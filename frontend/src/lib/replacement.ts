import type { ValidationResult } from "@/lib/types";

export type ReplacementPhase = "idle" | "uploading" | "uploaded" | "reading" | "checking";

export function replacementLabel(phase: ReplacementPhase, percent: number | null): string | null {
  if (phase === "uploading") {
    return percent != null && percent > 0 ? "Uploading…" : "Uploading new document…";
  }
  if (phase === "uploaded") {
    return "Upload complete.";
  }
  if (phase === "reading") {
    return "Reading document…";
  }
  if (phase === "checking") {
    return "Checking document…";
  }
  return null;
}

/** Stored badges and check rows stay hidden until the latest operation is idle. */
export function showStoredResults(phase: ReplacementPhase): boolean {
  return phase === "idle";
}

/**
 * Drop this file's rows and the shared rows. Other files keep their own rows.
 * Shared rows depend on the set of files, so they are stale as soon as one file changes.
 */
export function resultsAfterLocalChange(results: ValidationResult[], uploadId: string | null): ValidationResult[] {
  return results.filter((result) => {
    if (!result.uploaded_document_id) {
      return false;
    }
    return result.uploaded_document_id !== uploadId;
  });
}

export function restoreSuspended(current: ValidationResult[], suspended: ValidationResult[]): ValidationResult[] {
  const seen = new Set(current.map((result) => result.id));
  return [...current, ...suspended.filter((result) => !seen.has(result.id))];
}

export function validationOutcome(
  startedEpoch: number,
  latestEpoch: number,
  requestedAgain: boolean,
): { apply: boolean; repeat: boolean } {
  const apply = startedEpoch === latestEpoch;
  return { apply, repeat: requestedAgain || !apply };
}

export function metricsAfterReadFailure(body: { quality_metrics?: unknown; ocr_text_masked?: unknown } | null): {
  quality_metrics: Record<string, unknown>;
  ocr_text_masked: string | null;
} {
  const metrics = body?.quality_metrics;
  return {
    quality_metrics:
      metrics && typeof metrics === "object" && !Array.isArray(metrics) ? (metrics as Record<string, unknown>) : {},
    ocr_text_masked: typeof body?.ocr_text_masked === "string" ? body.ocr_text_masked : null,
  };
}
