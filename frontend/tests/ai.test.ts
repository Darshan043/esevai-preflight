import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  DAILY_AI_LIMIT_MESSAGE,
  EMPTY_OCR_AI_MESSAGE,
  EXTRACT_PARSE_MESSAGE,
  PROVIDER_BUSY_MESSAGE,
  PROVIDER_QUOTA_MESSAGE,
  adviceMatches,
  explainFailureMessage,
  extractFailureMessage,
  issueSignature,
  visibleAiDetails,
} from "../src/lib/ai.ts";
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

  it("keeps the application daily limit separate from provider limits", () => {
    assert.equal(explainFailureMessage(429, DAILY_AI_LIMIT_MESSAGE), DAILY_AI_LIMIT_MESSAGE);
    assert.equal(explainFailureMessage(429, PROVIDER_BUSY_MESSAGE), PROVIDER_BUSY_MESSAGE);
    assert.equal(explainFailureMessage(429, "other provider limit"), PROVIDER_BUSY_MESSAGE);
    assert.equal(explainFailureMessage(503, PROVIDER_QUOTA_MESSAGE), PROVIDER_QUOTA_MESSAGE);
    assert.equal(
      explainFailureMessage(503, "AI assistance is unavailable right now. Your standard checks still work."),
      "AI assistance is unavailable right now. Your standard checks still work.",
    );
    assert.equal(explainFailureMessage(503, "AI assistance is turned off."), "AI assistance is turned off.");
  });

  it("shows a parse error without collapsing other extract messages", () => {
    assert.equal(
      extractFailureMessage(409, "Read the document first"),
      "Read the document first, then try AI again.",
    );
    assert.equal(extractFailureMessage(409, EMPTY_OCR_AI_MESSAGE), EMPTY_OCR_AI_MESSAGE);
    assert.equal(extractFailureMessage(502, EXTRACT_PARSE_MESSAGE), EXTRACT_PARSE_MESSAGE);
    assert.equal(extractFailureMessage(503, "AI assistance is turned off."), "AI assistance is turned off.");
    assert.equal(extractFailureMessage(503, PROVIDER_QUOTA_MESSAGE), PROVIDER_QUOTA_MESSAGE);
    assert.equal(
      extractFailureMessage(503, "AI assistance is unavailable right now. Your standard checks still work."),
      "AI assistance is unavailable right now. Your standard checks still work.",
    );
    assert.equal(extractFailureMessage(429, DAILY_AI_LIMIT_MESSAGE), DAILY_AI_LIMIT_MESSAGE);
    assert.equal(
      extractFailureMessage(502, "SECRET stack trace with OCR"),
      "AI assistance is unavailable right now – your standard checks still work",
    );
  });
});
