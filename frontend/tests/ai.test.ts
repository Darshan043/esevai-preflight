import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { adviceMatches, issueSignature, visibleAiDetails } from "../src/lib/ai.ts";
import type { ValidationResult } from "../src/lib/types.ts";

function result(id: string, status: ValidationResult["status"]): ValidationResult {
  return {
    id,
    application_id: "app",
    uploaded_document_id: "upload",
    check_code: "date_validity",
    check_name: "Document date",
    status,
    message: status,
    fix_suggestion: "",
    details: {},
    created_at: "2026-11-18T00:00:00Z",
  };
}

describe("AI details and advice", () => {
  it("hides an empty extraction", () => {
    assert.equal(visibleAiDetails({}), null);
    assert.equal(visibleAiDetails({ holder_name: "  " }), null);
  });

  it("shows a saved name and ignores the bookkeeping block", () => {
    const details = visibleAiDetails({ holder_name: "Example Person", extraction_confidence: "high", _meta: { model: "hidden" } });
    assert.equal(details?.name, "Example Person");
    assert.equal(details?.confidence, "high");
  });

  it("matches advice only to the current warnings", () => {
    const warning = result("warn-1", "warning");
    const advice = {
      language: "en",
      generated_at: null,
      model: null,
      items: [{ id: "warn-1", explanation: "Show the date." }],
      overall_tip: "Check the page.",
    };
    assert.equal(adviceMatches(advice, [warning, result("pass-1", "pass")]), true);
    assert.equal(adviceMatches(advice, [result("other", "fail")]), false);
    assert.notEqual(issueSignature([warning]), issueSignature([result("other", "fail")]));
  });
});
