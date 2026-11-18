import type { AiDetails } from "@/lib/ai";

const rows: [keyof AiDetails, string][] = [
  ["documentType", "Document type"],
  ["name", "Name"],
  ["dateOfBirth", "Date of birth"],
  ["issueDate", "Issue date"],
  ["expiryDate", "Expiry date"],
  ["last4", "Last 4 digits"],
  ["confidence", "Confidence"],
];

export function AiDetailsPanel({ details }: { details: AiDetails }) {
  const shown = rows.filter(([key]) => details[key]);
  if (shown.length === 0) {
    return null;
  }
  return (
    <details className="mt-3 rounded-lg border border-line bg-white p-3">
      <summary className="min-h-11 cursor-pointer text-sm font-semibold text-navy">Details read by AI</summary>
      <p className="mt-2 text-sm text-muted">Read automatically – may contain mistakes</p>
      <dl className="mt-2 flex flex-col gap-1 text-sm text-ink">
        {shown.map(([key, label]) => (
          <div key={key} className="flex flex-wrap gap-2">
            <dt className="font-medium text-navy">{label}</dt>
            <dd>{details[key]}</dd>
          </div>
        ))}
      </dl>
      <p className="mt-2 text-sm text-muted">The checklist result comes from the rule-based checks.</p>
    </details>
  );
}
