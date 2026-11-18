import type { AdminDocumentInput, AdminRules, AdminServiceInput } from "@/lib/types";

export const ACCEPTED_FORMATS = ["jpg", "jpeg", "png", "pdf"] as const;
export const REQUIRED_FIELD_OPTIONS = [
  { id: "name", label: "Name" },
  { id: "number", label: "ID number" },
  { id: "date", label: "Date" },
] as const;

export const STATS_FOOTNOTE = "Statistics reflect current data; validation results are replaced whenever a check is re-run.";

const RULE_KEYS = [
  "min_width",
  "min_height",
  "min_blur_score",
  "min_brightness",
  "max_brightness",
  "id_number_pattern",
  "max_age_days",
  "check_name_match",
] as const;

export const DEFAULT_RULES: AdminRules = {
  min_width: 800,
  min_height: 600,
  min_blur_score: 100,
  min_brightness: 60,
  max_brightness: 220,
  id_number_pattern: null,
  max_age_days: null,
  check_name_match: false,
};

export const PHOTO_RULES: AdminRules = {
  min_width: 400,
  min_height: 500,
  min_blur_score: 80,
  min_brightness: 60,
  max_brightness: 220,
  id_number_pattern: null,
  max_age_days: null,
  check_name_match: false,
};

export function emptyService(): AdminServiceInput {
  return {
    slug: "",
    name_en: "",
    name_ta: "",
    description: "",
    is_active: false,
    is_verified: false,
    confirm_verified: false,
  };
}

export function emptyDocument(sortOrder = 10): AdminDocumentInput {
  return {
    code: "",
    name_en: "",
    name_ta: "",
    description: "",
    is_mandatory: true,
    accepted_formats: ["jpg", "jpeg", "png", "pdf"],
    max_size_mb: 5,
    validity_days: null,
    keywords: { en: [], ta: [] },
    required_fields: [],
    rules: { ...DEFAULT_RULES },
    sort_order: sortOrder,
    is_active: true,
  };
}

export function photoPreset(sortOrder = 10): AdminDocumentInput {
  return {
    ...emptyDocument(sortOrder),
    code: "applicant_photo",
    name_en: "Photo",
    keywords: { en: [], ta: [] },
    required_fields: [],
    rules: { ...PHOTO_RULES },
  };
}

export function pickRules(raw: Record<string, unknown> | null | undefined): AdminRules {
  const rules: AdminRules = {};
  if (!raw) {
    return rules;
  }
  for (const key of RULE_KEYS) {
    const value = raw[key];
    if (value === undefined) {
      continue;
    }
    (rules as Record<string, unknown>)[key] = value;
  }
  return rules;
}

export function slugFromName(name: string): string {
  return name
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 60);
}

export function errorFor(field: string, errors: Array<{ field: string; message: string }>): string | null {
  const match = errors.find((item) => item.field === field || item.field.startsWith(`${field}.`) || item.field.endsWith(`.${field}`));
  return match?.message ?? null;
}
