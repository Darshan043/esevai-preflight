import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { mapApiError } from "../src/lib/api-errors.ts";
import { shouldAutoResume } from "../src/lib/slot-status.ts";

describe("API error mapper", () => {
  it("reads the new envelope first", () => {
    const mapped = mapApiError(409, {
      error: {
        code: "CONFLICT",
        message: "Read the document first",
        request_id: "abc123",
      },
    });
    assert.equal(mapped.message, "Read the document first");
    assert.equal(mapped.code, "CONFLICT");
    assert.equal(mapped.requestId, "abc123");
  });

  it("falls back to a string detail", () => {
    const mapped = mapApiError(409, { detail: "Already processing" });
    assert.equal(mapped.message, "Already processing");
  });

  it("reads admin field errors from the envelope", () => {
    const mapped = mapApiError(422, {
      error: {
        code: "VALIDATION_ERROR",
        message: "Please check the highlighted fields and try again.",
        request_id: "rid",
        fields: [{ field: "slug", message: "Use a short slug." }],
      },
    });
    assert.equal(mapped.fields[0]?.field, "slug");
    assert.equal(mapped.fields[0]?.message, "Use a short slug.");
  });
});

describe("OCR auto-resume", () => {
  it("resumes an uploaded file", () => {
    assert.equal(shouldAutoResume("uploaded", "2026-11-19T00:00:00Z"), true);
  });

  it("resumes stalled processing after two minutes", () => {
    const now = Date.parse("2026-11-19T00:05:00Z");
    assert.equal(shouldAutoResume("processing", "2026-11-19T00:00:00Z", now), true);
    assert.equal(shouldAutoResume("processing", "2026-11-19T00:04:00Z", now), false);
  });

  it("does not resume a finished file", () => {
    assert.equal(shouldAutoResume("processed", "2026-11-19T00:00:00Z"), false);
  });
});
