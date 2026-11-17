// Server Supabase client. Reads the session from cookies.
// The proxy refreshes those cookies. This file only reads the signed-in user.

import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";
import { connection } from "next/server";

export type Profile = {
  full_name: string | null;
  role: string;
  preferred_language: string | null;
};

function publicConfig(): { url: string; anonKey: string } {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!url || !anonKey) {
    throw new Error("NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY must be set.");
  }
  return { url, anonKey };
}

export async function createClient() {
  const cookieStore = await cookies();
  const { url, anonKey } = publicConfig();

  return createServerClient(url, anonKey, {
    cookies: {
      getAll() {
        return cookieStore.getAll();
      },
      setAll(cookiesToSet) {
        // Server Components cannot always write cookies. The proxy does the refresh.
        try {
          cookiesToSet.forEach(({ name, value, options }) => {
            cookieStore.set(name, value, options);
          });
        } catch {
          // Ignore write failures here. The next request still refreshes in proxy.ts.
        }
      },
    },
  });
}

export async function getUserAndProfile(): Promise<{
  userId: string;
  email: string | null;
  profile: Profile | null;
} | null> {
  // Session checks read the clock inside Supabase. Wait until request time first.
  await connection();
  const supabase = await createClient();
  // getUser() checks the token with Supabase Auth. getSession() only reads the cookie.
  const { data } = await supabase.auth.getUser();
  const user = data.user;
  if (!user) {
    return null;
  }

  const { data: profile } = await supabase
    .from("profiles")
    .select("full_name, role, preferred_language")
    .eq("id", user.id)
    .maybeSingle();

  return {
    userId: user.id,
    email: user.email ?? null,
    profile: profile
      ? {
          full_name: profile.full_name,
          role: profile.role,
          preferred_language: profile.preferred_language,
        }
      : null,
  };
}
