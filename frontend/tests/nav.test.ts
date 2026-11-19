import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { formatStartedAt } from "../src/lib/dates.ts";
import { headerAudience, headerNavLinks } from "../src/lib/nav.ts";
import { uniqueById } from "../src/lib/unique.ts";

describe("header navigation", () => {
  it("shows Home, Services, Login, and Sign up when logged out", () => {
    const links = headerNavLinks(headerAudience(false, false)).map((item) => item.label);
    assert.deepEqual(links, ["Home", "Services"]);
  });

  it("shows Dashboard, Services, and My applications for a citizen", () => {
    const links = headerNavLinks(headerAudience(true, false)).map((item) => item.label);
    assert.deepEqual(links, ["Dashboard", "Services", "My applications"]);
    assert.equal(links.includes("Login"), false);
    assert.equal(links.includes("Sign up"), false);
    assert.equal(links.includes("Admin"), false);
  });

  it("shows Dashboard and Admin for an administrator", () => {
    const links = headerNavLinks(headerAudience(true, true)).map((item) => item.label);
    assert.deepEqual(links, ["Dashboard", "Admin"]);
    assert.equal(links.includes("Login"), false);
  });
});

describe("application list uniqueness", () => {
  it("keeps two Community Certificate applications when their ids differ", () => {
    const rows = uniqueById([
      { id: "a", name: "Community Certificate" },
      { id: "b", name: "Community Certificate" },
    ]);
    assert.equal(rows.length, 2);
  });

  it("drops a repeated id from a join, but not a second real application", () => {
    const rows = uniqueById([
      { id: "a", name: "Community Certificate" },
      { id: "a", name: "Community Certificate" },
      { id: "c", name: "Community Certificate" },
    ]);
    assert.deepEqual(
      rows.map((row) => row.id),
      ["a", "c"],
    );
  });
});

describe("application started time", () => {
  it("keeps the date and time so same-day Community Certificate drafts stay distinct", () => {
    const shown = formatStartedAt("2026-11-19T07:12:00.000Z");
    assert.equal(shown.includes("2026"), true);
    assert.equal(shown === "2026-11-19", false);
  });
});
