// Next.js 16 calls this file proxy.ts. Older versions called it middleware.ts.
// Session refresh, login redirects, and the /admin role check live in updateSession.
// The admin role is read from the profiles table, never from the browser.

import { type NextRequest } from "next/server";

import { updateSession } from "@/lib/supabase/update-session";

export async function proxy(request: NextRequest) {
  return updateSession(request);
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)"],
};
