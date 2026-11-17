// Refreshes the Supabase session and applies the login redirects.
// Next.js 16 runs this from src/proxy.ts before the page renders.

import { createServerClient } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";

function publicConfig(): { url: string; anonKey: string } {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!url || !anonKey) {
    throw new Error("NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY must be set.");
  }
  return { url, anonKey };
}

function copyCookies(from: NextResponse, to: NextResponse): NextResponse {
  from.cookies.getAll().forEach((cookie) => {
    to.cookies.set(cookie);
  });
  return to;
}

export async function updateSession(request: NextRequest) {
  let supabaseResponse = NextResponse.next({ request });
  const { url, anonKey } = publicConfig();

  const supabase = createServerClient(url, anonKey, {
    cookies: {
      getAll() {
        return request.cookies.getAll();
      },
      setAll(cookiesToSet) {
        cookiesToSet.forEach(({ name, value }) => {
          request.cookies.set(name, value);
        });
        supabaseResponse = NextResponse.next({ request });
        cookiesToSet.forEach(({ name, value, options }) => {
          supabaseResponse.cookies.set(name, value, options);
        });
      },
    },
  });

  // Validate the user with Auth. Do not trust getSession() by itself.
  const { data } = await supabase.auth.getUser();
  const user = data.user;
  const path = request.nextUrl.pathname;
  const isProtected =
    path === "/dashboard" ||
    path.startsWith("/dashboard/") ||
    path === "/admin" ||
    path.startsWith("/admin/") ||
    path === "/applications" ||
    path.startsWith("/applications/");
  const isAuthPage = path === "/login" || path === "/signup";

  if (!user && isProtected) {
    const redirectUrl = request.nextUrl.clone();
    redirectUrl.pathname = "/login";
    redirectUrl.searchParams.set("next", path);
    return copyCookies(supabaseResponse, NextResponse.redirect(redirectUrl));
  }

  if (user && isAuthPage) {
    const redirectUrl = request.nextUrl.clone();
    redirectUrl.pathname = "/dashboard";
    redirectUrl.search = "";
    return copyCookies(supabaseResponse, NextResponse.redirect(redirectUrl));
  }

  // Cache Components starts a 200 response before a page can call notFound().
  // Check an unknown service here so the status is 404 before rendering starts.
  const serviceMatch = /^\/services\/([^/]+)$/.exec(path);
  if (serviceMatch) {
    const slug = decodeURIComponent(serviceMatch[1]);
    const { data, error } = await supabase
      .from("services")
      .select("id")
      .eq("slug", slug)
      .eq("is_active", true)
      .maybeSingle();
    if (!error && !data) {
      const html = `<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Service not found</title></head><body><main><h1>Service not found</h1><p>We could not find that service. It may be inactive, or the link may be wrong.</p><p><a href="/services">Back to services</a></p></main></body></html>`;
      return copyCookies(
        supabaseResponse,
        new NextResponse(html, {
          status: 404,
          headers: { "content-type": "text/html; charset=utf-8" },
        }),
      );
    }
  }

  return supabaseResponse;
}
