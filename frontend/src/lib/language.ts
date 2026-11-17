// Only service and document names switch language.
// The rest of the interface stays in English.

export type Language = "en" | "ta";

export const LANGUAGE_COOKIE = "preferred_language";

export function parseLanguage(value: string | null | undefined): Language {
  return value === "ta" ? "ta" : "en";
}

export function pickName(
  item: { name_en: string; name_ta: string | null },
  lang: Language,
): string {
  if (lang === "ta" && item.name_ta && item.name_ta.trim()) {
    return item.name_ta;
  }
  return item.name_en;
}

export function writeLanguageCookie(lang: Language): void {
  document.cookie = `${LANGUAGE_COOKIE}=${lang}; Path=/; Max-Age=31536000; SameSite=Lax`;
}
