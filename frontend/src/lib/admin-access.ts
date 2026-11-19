// Pure access rules for /admin. Used by the proxy and the admin pages.
// The role must come from the profiles table, never from the browser.

export type AdminAccessInput = {
  signedIn: boolean;
  role: string | null;
  profileFound: boolean;
  profileLookupFailed: boolean;
};

export type AdminProxyDecision = "allow" | "login" | "dashboard";
export type AdminPageDecision = "allow" | "login" | "forbidden";

export function isAdminPath(pathname: string): boolean {
  return pathname === "/admin" || pathname.startsWith("/admin/");
}

function hasAdminRole(input: AdminAccessInput): boolean {
  return !input.profileLookupFailed && input.profileFound && input.role === "admin";
}

export function adminProxyDecision(input: AdminAccessInput): AdminProxyDecision {
  if (!input.signedIn) {
    return "login";
  }
  // Missing profile or a failed lookup is a deny, not a pass.
  if (!hasAdminRole(input)) {
    return "dashboard";
  }
  return "allow";
}

export function adminPageDecision(input: AdminAccessInput): AdminPageDecision {
  if (!input.signedIn) {
    return "login";
  }
  if (!hasAdminRole(input)) {
    return "forbidden";
  }
  return "allow";
}
