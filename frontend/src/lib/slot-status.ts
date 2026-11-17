import type { UploadedDocument, ValidationResult } from "@/lib/types";

export type SlotStatus =
  | "Pending"
  | "Uploaded"
  | "Processing"
  | "Processed"
  | "Passed"
  | "Check advised"
  | "Needs fix"
  | "Failed";

// Turns one checklist row plus its saved file into a label the citizen can read.
export function slotStatus(
  upload: Pick<UploadedDocument, "id" | "status"> | null,
  results: ValidationResult[],
): SlotStatus {
  if (!upload) {
    return "Pending";
  }
  if (upload.status === "uploaded") {
    return "Uploaded";
  }
  if (upload.status === "processing") {
    return "Processing";
  }
  if (upload.status === "failed") {
    return "Failed";
  }

  const own = results.filter((result) => result.uploaded_document_id === upload.id);
  if (own.length === 0) {
    return "Processed";
  }
  if (own.some((result) => result.status === "fail")) {
    return "Needs fix";
  }
  if (own.some((result) => result.status === "warning")) {
    return "Check advised";
  }
  return "Passed";
}
