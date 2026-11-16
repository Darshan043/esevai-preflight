// Browser Supabase client. Uses the public anon key only.

import { createBrowserClient } from "@supabase/ssr";

function publicConfig(): { url: string; anonKey: string } {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!url || !anonKey) {
    throw new Error("NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY must be set.");
  }
  return { url, anonKey };
}

export function createClient() {
  const { url, anonKey } = publicConfig();
  return createBrowserClient(url, anonKey);
}
