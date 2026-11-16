// Shared navigation. Auth links are filled in by the browser after mount.

import Link from "next/link";

import { HeaderAuth } from "@/components/HeaderAuth";

export function SiteHeader() {
  return (
    <header className="border-b border-zinc-200 bg-white">
      <div className="mx-auto flex w-full max-w-3xl flex-wrap items-center gap-3 px-6 py-4">
        <Link href="/" className="text-base font-semibold text-zinc-900">
          e-Sevai Pre-Flight
        </Link>
        <HeaderAuth />
      </div>
    </header>
  );
}
