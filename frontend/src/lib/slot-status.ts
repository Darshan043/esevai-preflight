import type { UploadedDocument, ValidationResult } from "@/lib/types";

export type SlotStatus = "Pending" | "Uploaded" | "Processing" | "Passed" | "Needs fix" | "Failed";

// Turns one checklist row plus its saved file into a label the citizen can read.
export function slotStatus(
  upload: UploadedDocument | null,
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

  const failed = results.some(
    (result) => result.uploaded_document_id === upload.id && result.status === "fail",
  );
  return failed ? "Needs fix" : "Passed";
}
