"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { writeLanguageCookie, type Language } from "@/lib/language";
import { createClient } from "@/lib/supabase/client";

export function LanguageToggle({
  language,
  userId,
}: {
  language: Language;
  userId: string | null;
}) {
  const router = useRouter();
  const [pending, setPending] = useState(false);

  async function choose(next: Language) {
    if (next === language || pending) {
      return;
    }
    setPending(true);
    writeLanguageCookie(next);
    if (userId) {
      const supabase = createClient();
      await supabase.from("profiles").update({ preferred_language: next }).eq("id", userId);
    }
    router.refresh();
    setPending(false);
  }

  return (
    <div className="inline-flex overflow-hidden rounded-lg border border-white/30" role="group" aria-label="Document language">
      <button
        type="button"
        aria-pressed={language === "en"}
        disabled={pending}
        onClick={() => {
          void choose("en");
        }}
        className={`inline-flex min-h-11 items-center px-3 text-sm ${
          language === "en" ? "bg-white text-navy" : "bg-transparent text-white"
        }`}
      >
        EN
      </button>
      <button
        type="button"
        aria-pressed={language === "ta"}
        disabled={pending}
        onClick={() => {
          void choose("ta");
        }}
        className={`inline-flex min-h-11 items-center px-3 text-sm ${
          language === "ta" ? "bg-white text-navy" : "bg-transparent text-white"
        }`}
      >
        தமிழ்
      </button>
    </div>
  );
}
