"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { LanguageToggle } from "@/components/LanguageToggle";
import { SignOutButton } from "@/components/SignOutButton";
import { headerAudience, headerNavLinks } from "@/lib/nav";
import { createClient } from "@/lib/supabase/client";
import type { Language } from "@/lib/language";

type AuthView = "logged-out" | "logged-in";

export function HeaderAuth({
  initialLanguage,
  initialSignedIn = false,
  initialIsAdmin = false,
  initialUserId = null,
}: {
  initialLanguage: Language;
  initialSignedIn?: boolean;
  initialIsAdmin?: boolean;
  initialUserId?: string | null;
}) {
  const [state, setState] = useState<AuthView>(initialSignedIn ? "logged-in" : "logged-out");
  const [isAdmin, setIsAdmin] = useState(initialIsAdmin);
  const [userId, setUserId] = useState<string | null>(initialUserId);
  const [language, setLanguage] = useState<Language>(initialLanguage);

  useEffect(() => {
    const supabase = createClient();
    let cancelled = false;

    async function applyUser(nextUserId: string | null) {
      if (cancelled) {
        return;
      }
      if (!nextUserId) {
        setIsAdmin(false);
        setUserId(null);
        setLanguage(initialLanguage);
        setState("logged-out");
        return;
      }
      setUserId(nextUserId);
      setState("logged-in");
      const { data: profile, error: profileError } = await supabase
        .from("profiles")
        .select("role, preferred_language")
        .eq("id", nextUserId)
        .maybeSingle();
      if (cancelled) {
        return;
      }
      setIsAdmin(!profileError && profile?.role === "admin");
      setLanguage(
        profile?.preferred_language === "ta" || profile?.preferred_language === "en"
          ? profile.preferred_language
          : initialLanguage,
      );
    }

    const { data } = supabase.auth.onAuthStateChange((_event, session) => {
      void applyUser(session?.user?.id ?? null);
    });

    void supabase.auth.getUser().then(({ data: userData }) => {
      void applyUser(userData.user?.id ?? null);
    });

    return () => {
      cancelled = true;
      data.subscription.unsubscribe();
    };
  }, [initialLanguage]);

  const audience = headerAudience(state === "logged-in", isAdmin);
  const links = headerNavLinks(audience);

  return (
    <>
      {links.map((item) => (
        <Link key={item.href} href={item.href} className="nav-link">
          {item.label}
        </Link>
      ))}
      {state === "logged-in" ? (
        <SignOutButton className="nav-link" />
      ) : (
        <>
          <Link href="/login" className="nav-link">
            Login
          </Link>
          <Link href="/signup" className="btn-primary">
            Sign up
          </Link>
        </>
      )}
      <LanguageToggle userId={userId} language={language} />
    </>
  );
}
