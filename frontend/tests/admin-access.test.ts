import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { adminPageDecision, adminProxyDecision, isAdminPath } from "../src/lib/admin-access.ts";

describe("admin paths", () => {
  it("treats /admin and nested admin pages as admin routes", () => {
    assert.equal(isAdminPath("/admin"), true);
    assert.equal(isAdminPath("/admin/services"), true);
    assert.equal(isAdminPath("/admin/services/new"), true);
    assert.equal(isAdminPath("/admin/checks"), true);
  });

  it("does not treat citizen routes as admin routes", () => {
    assert.equal(isAdminPath("/dashboard"), false);
    assert.equal(isAdminPath("/applications"), false);
    assert.equal(isAdminPath("/services"), false);
  });
});

describe("proxy decision for /admin", () => {
  it("sends a signed-out visitor to login", () => {
    assert.equal(
      adminProxyDecision({ signedIn: false, role: null, profileFound: false, profileLookupFailed: false }),
      "login",
    );
  });

  it("sends a citizen away from /admin and nested admin pages", () => {
    const citizen = { signedIn: true, role: "citizen", profileFound: true, profileLookupFailed: false };
    assert.equal(adminProxyDecision(citizen), "dashboard");
    assert.equal(isAdminPath("/admin/services"), true);
  });

  it("allows an admin into /admin", () => {
    assert.equal(
      adminProxyDecision({ signedIn: true, role: "admin", profileFound: true, profileLookupFailed: false }),
      "allow",
    );
  });

  it("denies a missing profile", () => {
    assert.equal(
      adminProxyDecision({ signedIn: true, role: null, profileFound: false, profileLookupFailed: false }),
      "dashboard",
    );
  });

  it("denies a profile lookup failure", () => {
    assert.equal(
      adminProxyDecision({ signedIn: true, role: "admin", profileFound: true, profileLookupFailed: true }),
      "dashboard",
    );
  });
});

describe("admin page decision", () => {
  it("forbids a citizen on /admin and nested pages", () => {
    const citizen = { signedIn: true, role: "citizen", profileFound: true, profileLookupFailed: false };
    assert.equal(adminPageDecision(citizen), "forbidden");
  });

  it("allows an admin", () => {
    assert.equal(
      adminPageDecision({ signedIn: true, role: "admin", profileFound: true, profileLookupFailed: false }),
      "allow",
    );
  });

  it("forbids a missing profile", () => {
    assert.equal(
      adminPageDecision({ signedIn: true, role: null, profileFound: false, profileLookupFailed: false }),
      "forbidden",
    );
  });

  it("forbids a profile lookup failure even if a role string is present", () => {
    assert.equal(
      adminPageDecision({ signedIn: true, role: "admin", profileFound: true, profileLookupFailed: true }),
      "forbidden",
    );
  });

  it("sends a signed-out visitor to login", () => {
    assert.equal(
      adminPageDecision({ signedIn: false, role: null, profileFound: false, profileLookupFailed: false }),
      "login",
    );
  });
});
