import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  metricsAfterReadFailure,
  replacementLabel,
  restoreSuspended,
  resultsAfterLocalChange,
  showStoredResults,
  validationOutcome,
  type ReplacementPhase,
} from "../src/lib/replacement.ts";
import type { ValidationResult } from "../src/lib/types.ts";

function result(id: string, uploadId: string | null, status: ValidationResult["status"] = "pass"): ValidationResult {
  return {
    id,
    application_id: "app",
    uploaded_document_id: uploadId,
    check_code: id,
    check_name: id,
    status,
    message: status,
    fix_suggestion: null,
    details: {},
    created_at: "2026-11-17T00:00:00Z",
  };
}

describe("replacement display", () => {
  it("hides the previous results as soon as replacement starts", () => {
    const rows = [result("own", "doc-1", "fail"), result("shared", null, "fail"), result("other", "doc-2", "pass")];
    const kept = resultsAfterLocalChange(rows, "doc-1");
    assert.deepEqual(kept.map((row) => row.id), ["other"]);
    assert.equal(showStoredResults("uploading"), false);
    assert.equal(showStoredResults("reading"), false);
    assert.equal(showStoredResults("checking"), false);
  });

  it("shows stored results only after the operation is idle", () => {
    const phases: ReplacementPhase[] = ["uploading", "uploaded", "reading", "checking", "idle"];
    const visible = phases.filter((phase) => showStoredResults(phase));
    assert.deepEqual(visible, ["idle"]);
    assert.equal(replacementLabel("uploaded", null), "Upload complete.");
    assert.equal(replacementLabel("reading", null), "Reading document…");
    assert.equal(replacementLabel("checking", null), "Checking document…");
    assert.equal(replacementLabel("uploading", null), "Uploading new document…");
    assert.equal(replacementLabel("uploading", 40), "Uploading…");
  });

  it("does not let an older validation response replace a newer one", () => {
    const stale = validationOutcome(1, 2, false);
    assert.equal(stale.apply, false);
    assert.equal(stale.repeat, true);
    const current = validationOutcome(2, 2, false);
    assert.equal(current.apply, true);
    assert.equal(current.repeat, false);
    const repeated = validationOutcome(2, 2, true);
    assert.equal(repeated.apply, true);
    assert.equal(repeated.repeat, true);
  });

  it("restores the previous rows when the new upload fails", () => {
    const kept = [result("other", "doc-2")];
    const suspended = [result("own", "doc-1", "fail"), result("shared", null)];
    const restored = restoreSuspended(kept, suspended);
    assert.deepEqual(restored.map((row) => row.id), ["other", "own", "shared"]);
  });

  it("does not keep the previous text when reading fails", () => {
    const failed = metricsAfterReadFailure({
      quality_metrics: { error: "We could not read this file." },
      ocr_text_masked: null,
    });
    assert.equal(failed.ocr_text_masked, null);
    assert.equal(failed.quality_metrics.error, "We could not read this file.");
    const empty = metricsAfterReadFailure(null);
    assert.deepEqual(empty.quality_metrics, {});
    assert.equal(empty.ocr_text_masked, null);
  });
});
