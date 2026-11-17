// Shared navigation. The brand is static. Account links load in the browser.

import Link from "next/link";
import { cookies } from "next/headers";
import { Suspense } from "react";
import { connection } from "next/server";

import { HeaderAuth } from "@/components/HeaderAuth";
import { LANGUAGE_COOKIE, parseLanguage } from "@/lib/language";

async function HeaderWithLanguage() {
  // Wait until the real request so the language cookie is not read during prerender.
  await connection();
  const store = await cookies();
  const language = parseLanguage(store.get(LANGUAGE_COOKIE)?.value);
  return <HeaderAuth key={language} initialLanguage={language} />;
}

export function SiteHeader() {
  return (
    <header className="border-b border-zinc-200 bg-white">
      <div className="mx-auto flex w-full max-w-5xl flex-wrap items-center gap-3 px-4 py-3 sm:px-6">
        <Link
          href="/"
          className="inline-flex min-h-11 items-center text-base font-semibold text-zinc-900 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-zinc-900"
        >
          e-Sevai Pre-Flight
        </Link>
        <Suspense fallback={<HeaderAuth key="en" initialLanguage="en" />}>
          <HeaderWithLanguage />
        </Suspense>
      </div>
    </header>
  );
}
