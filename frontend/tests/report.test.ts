import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { issueListKey } from "../src/lib/report.ts";

describe("report list keys", () => {
  it("keeps two missing_document rows unique", () => {
    const codes = ["missing_document", "missing_document", "name_consistency"];
    const keys = codes.map((code, index) => issueListKey(code, index));
    assert.deepEqual(keys, ["missing_document-0", "missing_document-1", "name_consistency-2"]);
    assert.equal(new Set(keys).size, keys.length);
  });
});
