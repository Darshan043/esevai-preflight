"use client";

// Reads the session after the page is in the browser.
// The first render always shows the logged-out links so prerender stays stable.

import Link from "next/link";
import { Menu, X } from "lucide-react";
import { useEffect, useState } from "react";

import { LanguageToggle } from "@/components/LanguageToggle";
import { SignOutButton } from "@/components/SignOutButton";
import { parseLanguage, writeLanguageCookie, type Language } from "@/lib/language";
import { createClient } from "@/lib/supabase/client";

type HeaderState = "logged-out" | "logged-in";

const linkClass =
  "inline-flex min-h-11 items-center rounded-md px-2 text-sm text-zinc-800 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-zinc-900";

export function HeaderAuth({ initialLanguage }: { initialLanguage: Language }) {
  const [state, setState] = useState<HeaderState>("logged-out");
  const [isAdmin, setIsAdmin] = useState(false);
  const [userId, setUserId] = useState<string | null>(null);
  const [profileLanguage, setProfileLanguage] = useState<Language | null>(null);
  const [menuOpen, setMenuOpen] = useState(false);
  const language = profileLanguage ?? initialLanguage;

  useEffect(() => {
    let cancelled = false;

    async function loadSession() {
      try {
        const supabase = createClient();
        const { data, error } = await supabase.auth.getUser();
        if (cancelled) {
          return;
        }
        if (error || !data.user) {
          setIsAdmin(false);
          setUserId(null);
          setState("logged-out");
          return;
        }

        const { data: profile, error: profileError } = await supabase
          .from("profiles")
          .select("role, preferred_language")
          .eq("id", data.user.id)
          .maybeSingle();
        if (cancelled) {
          return;
        }
        // A failed profile read must not show the admin link.
        setIsAdmin(!profileError && profile?.role === "admin");
        setUserId(data.user.id);
        setState("logged-in");
        const savedLanguage = parseLanguage(profile?.preferred_language);
        if (!profileError && profile?.preferred_language && savedLanguage !== initialLanguage) {
          writeLanguageCookie(savedLanguage);
          setProfileLanguage(savedLanguage);
        }
      } catch {
        if (!cancelled) {
          setIsAdmin(false);
          setUserId(null);
          setState("logged-out");
        }
      }
    }

    void loadSession();
    return () => {
      cancelled = true;
    };
  }, [initialLanguage]);

  const signedIn = state === "logged-in";

  return (
    <>
      <button
        type="button"
        className="ml-auto inline-flex min-h-11 items-center gap-2 rounded-md px-3 text-sm text-zinc-800 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-zinc-900 md:hidden"
        aria-expanded={menuOpen}
        aria-controls="site-menu"
        onClick={() => setMenuOpen((open) => !open)}
      >
        {menuOpen ? <X aria-hidden="true" className="h-5 w-5" /> : <Menu aria-hidden="true" className="h-5 w-5" />}
        {menuOpen ? "Close" : "Menu"}
      </button>
      <div
        id="site-menu"
        className={`${menuOpen ? "flex" : "hidden"} w-full flex-col gap-2 md:ml-auto md:flex md:w-auto md:flex-row md:items-center md:gap-3`}
      >
        <nav className="flex flex-col gap-1 md:flex-row md:items-center" aria-label="Main">
          <Link href="/" className={linkClass}>
            Home
          </Link>
          <Link href="/services" className={linkClass}>
            Services
          </Link>
          {signedIn ? (
            <Link href="/applications" className={linkClass}>
              My applications
            </Link>
          ) : null}
          {signedIn ? (
            <Link href="/dashboard" className={linkClass}>
              Dashboard
            </Link>
          ) : null}
          {signedIn && isAdmin ? (
            <Link href="/admin" className={linkClass}>
              Admin
            </Link>
          ) : null}
        </nav>
        <LanguageToggle language={language} userId={userId} />
        <div className="flex flex-wrap items-center gap-2">
          {signedIn ? (
            <SignOutButton />
          ) : (
            <>
              <Link href="/login" className={linkClass}>
                Login
              </Link>
              <Link
                href="/signup"
                className="inline-flex min-h-11 items-center rounded-md bg-zinc-900 px-3 text-sm text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-zinc-900"
              >
                Sign up
              </Link>
            </>
          )}
        </div>
      </div>
    </>
  );
}
