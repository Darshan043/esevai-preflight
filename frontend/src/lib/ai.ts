import type { ValidationResult } from "@/lib/types";

export type AiDetails = {
  documentType: string | null;
  name: string | null;
  dateOfBirth: string | null;
  issueDate: string | null;
  expiryDate: string | null;
  last4: string | null;
  confidence: string | null;
};

export type AiAdvice = {
  language: string | null;
  generated_at: string | null;
  model: string | null;
  items: { id: string; explanation: string }[];
  overall_tip: string | null;
};

const DETAIL_KEYS = [
  "document_type_guess",
  "holder_name",
  "date_of_birth",
  "issue_date",
  "expiry_date",
  "id_last4",
  "extraction_confidence",
] as const;

export function visibleAiDetails(fields: Record<string, unknown> | null | undefined): AiDetails | null {
  if (!fields) {
    return null;
  }
  const present = DETAIL_KEYS.some((key) => typeof fields[key] === "string" && fields[key].trim() !== "");
  if (!present) {
    return null;
  }
  return {
    documentType: textField(fields, "document_type_guess"),
    name: textField(fields, "holder_name"),
    dateOfBirth: textField(fields, "date_of_birth"),
    issueDate: textField(fields, "issue_date"),
    expiryDate: textField(fields, "expiry_date"),
    last4: textField(fields, "id_last4"),
    confidence: textField(fields, "extraction_confidence"),
  };
}

export function issueSignature(results: ValidationResult[]): string {
  return results
    .filter((result) => result.status !== "pass")
    .map((result) => `${result.id}|${result.status}|${result.message ?? ""}`)
    .sort()
    .join("\n");
}

export function adviceMatches(advice: AiAdvice | null, results: ValidationResult[]): boolean {
  if (!advice || advice.items.length === 0) {
    return false;
  }
  const current = new Set(results.filter((result) => result.status !== "pass").map((result) => result.id));
  const explained = new Set(advice.items.map((item) => item.id));
  if (current.size === 0 || current.size !== explained.size) {
    return false;
  }
  for (const id of current) {
    if (!explained.has(id)) {
      return false;
    }
  }
  return true;
}

function textField(fields: Record<string, unknown>, key: string): string | null {
  const value = fields[key];
  return typeof value === "string" && value.trim() ? value.trim() : null;
}
