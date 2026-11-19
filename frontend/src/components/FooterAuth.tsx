"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { createClient } from "@/lib/supabase/client";

function FooterLink({ href, label }: { href: string; label: string }) {
  return (
    <li>
      <Link href={href} className="underline-offset-2 hover:text-white hover:underline">
        {label}
      </Link>
    </li>
  );
}

export function FooterAuth() {
  const [signedIn, setSignedIn] = useState<boolean | null>(null);

  useEffect(() => {
    const supabase = createClient();
    const { data } = supabase.auth.onAuthStateChange((_event, session) => {
      setSignedIn(Boolean(session?.user));
    });
    void supabase.auth.getUser().then(({ data: userData }) => {
      setSignedIn(Boolean(userData.user));
    });
    return () => {
      data.subscription.unsubscribe();
    };
  }, []);

  if (signedIn) {
    return (
      <>
        <FooterLink href="/dashboard" label="Dashboard" />
        <FooterLink href="/services" label="Services" />
        <FooterLink href="/applications" label="My applications" />
      </>
    );
  }

  return (
    <>
      <FooterLink href="/" label="Home" />
      <FooterLink href="/services" label="Services" />
      {signedIn === false ? (
        <>
          <FooterLink href="/login" label="Login" />
          <FooterLink href="/signup" label="Create account" />
        </>
      ) : null}
    </>
  );
}
