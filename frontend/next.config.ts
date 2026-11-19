import type { NextConfig } from "next";

function originFromEnv(name: "NEXT_PUBLIC_API_URL" | "NEXT_PUBLIC_SUPABASE_URL"): string | null {
  const raw = process.env[name]?.trim();
  if (!raw) {
    return null;
  }
  try {
    return new URL(raw).origin;
  } catch {
    return null;
  }
}

const apiOrigin = originFromEnv("NEXT_PUBLIC_API_URL");
const supabaseOrigin = originFromEnv("NEXT_PUBLIC_SUPABASE_URL");

// connect-src is built at Next.js BUILD time from NEXT_PUBLIC_API_URL and
// NEXT_PUBLIC_SUPABASE_URL. Changing those names requires a redeploy.
// localhost / 127.0.0.1 entries are documented development fallbacks only.
const connectSrc = [
  "'self'",
  "https:",
  "wss:",
  "http://localhost:8000",
  "http://127.0.0.1:8000",
  "ws://localhost:3000",
  "ws://127.0.0.1:3000",
  apiOrigin,
  supabaseOrigin,
]
  .filter((value, index, all): value is string => Boolean(value) && all.indexOf(value) === index)
  .join(" ");

const contentSecurityPolicy = [
  "default-src 'self'",
  "script-src 'self' 'unsafe-inline' 'unsafe-eval'",
  "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
  "font-src 'self' https://fonts.gstatic.com data:",
  "img-src 'self' data: blob: https:",
  `connect-src ${connectSrc}`,
  "frame-ancestors 'none'",
  "base-uri 'self'",
  "form-action 'self'",
].join("; ");

const securityHeaders = [
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "Referrer-Policy", value: "no-referrer" },
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
  { key: "Content-Security-Policy", value: contentSecurityPolicy },
];

const nextConfig: NextConfig = {
  /* config options here */
  cacheComponents: true,
  partialPrefetching: true,
  output: "standalone",
  experimental: {
    authInterrupts: true,
  },
  async headers() {
    return [{ source: "/:path*", headers: securityHeaders }];
  },
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
