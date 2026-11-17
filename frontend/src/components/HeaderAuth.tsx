"use client";

// Reads the session after the page is in the browser.
// The first render always shows the logged-out links so prerender stays stable.

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Menu, X } from "lucide-react";
import { useEffect, useState } from "react";

import { LanguageToggle } from "@/components/LanguageToggle";
import { SignOutButton } from "@/components/SignOutButton";
import { parseLanguage, writeLanguageCookie, type Language } from "@/lib/language";
import { createClient } from "@/lib/supabase/client";

type HeaderState = "logged-out" | "logged-in";

const linkClass = "nav-link inline-flex";

function isCurrent(href: string, pathname: string) {
  return href === "/" ? pathname === "/" : pathname === href || pathname.startsWith(`${href}/`);
}

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

  useEffect(() => {
    const supabase = createClient();
    const { data } = supabase.auth.onAuthStateChange((event) => {
      if (event === "SIGNED_OUT") {
        setIsAdmin(false);
        setUserId(null);
        setState("logged-out");
        setMenuOpen(false);
      }
    });
    return () => {
      data.subscription.unsubscribe();
    };
  }, []);

  const signedIn = state === "logged-in";
  const pathname = usePathname();

  return (
    <>
      <button
        type="button"
        className="ml-auto inline-flex min-h-11 items-center gap-2 rounded-md px-3 text-white md:hidden"
        aria-expanded={menuOpen}
        aria-controls="site-menu"
        onClick={() => setMenuOpen((open) => !open)}
      >
        {menuOpen ? <X aria-hidden="true" className="h-5 w-5" /> : <Menu aria-hidden="true" className="h-5 w-5" />}
        {menuOpen ? "Close" : "Menu"}
      </button>
      <div
        id="site-menu"
        className={`${menuOpen ? "flex" : "hidden"} w-full flex-col gap-2 py-2 md:flex md:flex-row md:items-center md:gap-3 md:py-0`}
      >
        <nav className="flex flex-col gap-1 md:mr-auto md:flex-row md:items-center" aria-label="Main">
          <Link href="/" className={linkClass} aria-current={isCurrent("/", pathname) ? "page" : undefined}>
            Home
          </Link>
          <Link href="/services" className={linkClass} aria-current={isCurrent("/services", pathname) ? "page" : undefined}>
            Services
          </Link>
          {signedIn ? (
            <Link href="/applications" className={linkClass} aria-current={isCurrent("/applications", pathname) ? "page" : undefined}>
              My applications
            </Link>
          ) : null}
          {signedIn ? (
            <Link href="/dashboard" className={linkClass} aria-current={isCurrent("/dashboard", pathname) ? "page" : undefined}>
              Dashboard
            </Link>
          ) : null}
          {signedIn && isAdmin ? (
            <Link href="/admin" className={linkClass} aria-current={isCurrent("/admin", pathname) ? "page" : undefined}>
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
              <Link href="/login" className={linkClass} aria-current={isCurrent("/login", pathname) ? "page" : undefined}>
                Login
              </Link>
              <Link href="/signup" className="btn-primary" aria-current={isCurrent("/signup", pathname) ? "page" : undefined}>
                Sign up
              </Link>
            </>
          )}
        </div>
      </div>
    </>
  );
}
