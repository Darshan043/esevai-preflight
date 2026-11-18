// Shared navigation. The brand is static. Account links load in the browser.

import Link from "next/link";
import { cookies } from "next/headers";
import { Suspense } from "react";
import { connection } from "next/server";
import { FileText } from "lucide-react";

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
    <header className="border-b border-navy bg-white text-navy print:hidden">
      <a href="#content" className="skip-link">
        Skip to content
      </a>
      <div className="utility-bar">
        <div className="mx-auto flex w-full max-w-6xl items-center justify-between gap-3 px-4 py-2 sm:px-6">
          <p>Independent document pre-check. Not an official government service.</p>
          <p className="hidden sm:block">English and Tamil document names</p>
        </div>
      </div>
      <div className="identity-bar" aria-hidden="true">
        <span className="bg-[#ff9933]" />
        <span className="bg-white" />
        <span className="bg-[#138808]" />
      </div>
      <div className="mx-auto flex w-full max-w-6xl items-center px-4 py-3.5 sm:px-6">
        <Link href="/" className="inline-flex min-w-0 items-center gap-3">
          {/* Served as the original file so the emblem is not recompressed or stretched. */}
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src="/tn-emblem.png"
            alt="Tamil Nadu government emblem"
            width={571}
            height={622}
            className="h-12 w-auto shrink-0 sm:h-14"
          />
          <span className="grid h-10 w-10 shrink-0 place-items-center rounded-md bg-navy text-white sm:h-11 sm:w-11" aria-hidden="true">
            <FileText className="h-5 w-5" />
          </span>
          <span className="min-w-0">
            <span className="block text-base font-semibold leading-5 tracking-tight text-navy sm:text-lg">e-Sevai Pre-Flight</span>
            <span className="mt-0.5 block text-xs font-medium text-muted">Independent document assistant</span>
          </span>
        </Link>
      </div>
      <div className="bg-navy text-white">
        <div className="mx-auto flex w-full max-w-6xl flex-wrap items-center gap-2 px-4 py-1.5 sm:px-6">
          <Suspense fallback={<HeaderAuth key="en" initialLanguage="en" />}>
            <HeaderWithLanguage />
          </Suspense>
        </div>
      </div>
    </header>
  );
}
