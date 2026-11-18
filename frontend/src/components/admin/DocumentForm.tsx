"use client";

import { useEffect, useMemo, useState, type ReactNode } from "react";

import { ACCEPTED_FORMATS, errorFor, PHOTO_RULES, REQUIRED_FIELD_OPTIONS } from "@/lib/admin-defaults";
import type { AdminDocumentInput, AdminFieldError } from "@/lib/types";

function testPattern(pattern: string, sample: string): string {
  if (!pattern.trim()) {
    return "Enter a pattern first.";
  }
  try {
    return new RegExp(pattern).test(sample) ? "This sample matches." : "This sample does not match.";
  } catch {
    return "This pattern is not valid JavaScript. The server also checks Python regex safety.";
  }
}

export function DocumentForm({
  initial,
  lockedCode,
  serverErrors,
  onSave,
  onCancel,
  busy,
}: {
  initial: AdminDocumentInput;
  lockedCode: boolean;
  serverErrors: AdminFieldError[];
  onSave: (payload: AdminDocumentInput) => void;
  onCancel: () => void;
  busy: boolean;
}) {
  const [form, setForm] = useState<AdminDocumentInput>(initial);
  const [sample, setSample] = useState("123456789012");
  const [patternNote, setPatternNote] = useState<string | null>(null);
  const snapshot = useMemo(() => JSON.stringify(initial), [initial]);
  const dirty = JSON.stringify(form) !== snapshot;
  const photoType = form.keywords.en.length === 0 && form.keywords.ta.length === 0 && form.required_fields.length === 0;

  useEffect(() => {
    function warn(event: BeforeUnloadEvent) {
      if (dirty) {
        event.preventDefault();
      }
    }
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [dirty]);

  function update<K extends keyof AdminDocumentInput>(key: K, value: AdminDocumentInput[K]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  function addKeyword(lang: "en" | "ta", raw: string) {
    const word = raw.trim();
    if (!word) {
      return;
    }
    setForm((current) => {
      const list = current.keywords[lang];
      if (list.some((item) => item.toLowerCase() === word.toLowerCase())) {
        return current;
      }
      return { ...current, keywords: { ...current.keywords, [lang]: [...list, word] } };
    });
  }

  function applyPhotoPreset() {
    setForm((current) => ({
      ...current,
      keywords: { en: [], ta: [] },
      required_fields: [],
      rules: { ...PHOTO_RULES },
    }));
  }

  return (
    <div className="fixed inset-0 z-40 flex items-start justify-center overflow-y-auto bg-navy/50 p-4" role="dialog" aria-modal="true" aria-labelledby="document-form-title">
      <form
        className="panel my-6 w-full max-w-2xl"
        onSubmit={(event) => {
          event.preventDefault();
          onSave(form);
        }}
      >
        <h2 id="document-form-title" className="text-xl font-semibold text-navy">
          Required document
        </h2>
        {dirty ? <p className="mt-2 text-sm text-saffron">You have unsaved changes.</p> : null}
        <Field label="Code" help="Snake_case, unique on this service. Locked after a file has been uploaded." error={errorFor("code", serverErrors)}>
          <input className="field" value={form.code} disabled={lockedCode} onChange={(event) => update("code", event.target.value)} required />
        </Field>
        <Field label="English name" error={errorFor("name_en", serverErrors)}>
          <input className="field" value={form.name_en} onChange={(event) => update("name_en", event.target.value)} required />
        </Field>
        <Field label="Tamil name" error={errorFor("name_ta", serverErrors)}>
          <input className="field" value={form.name_ta ?? ""} onChange={(event) => update("name_ta", event.target.value)} />
        </Field>
        <Field label="Help text" error={errorFor("description", serverErrors)}>
          <textarea className="field min-h-20" value={form.description ?? ""} onChange={(event) => update("description", event.target.value)} />
        </Field>
        <label className="mt-4 flex items-center gap-2 text-sm">
          <input type="checkbox" checked={form.is_mandatory} onChange={(event) => update("is_mandatory", event.target.checked)} />
          Mandatory
        </label>
        <label className="mt-2 flex items-center gap-2 text-sm">
          <input type="checkbox" checked={form.is_active} onChange={(event) => update("is_active", event.target.checked)} />
          Active (shown to citizens)
        </label>
        <fieldset className="mt-4">
          <legend className="text-sm font-medium text-navy">Accepted formats</legend>
          <p className="text-sm text-muted">JPG, JPEG, PNG, or PDF only.</p>
          <div className="mt-2 flex flex-wrap gap-3">
            {ACCEPTED_FORMATS.map((format) => (
              <label key={format} className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={form.accepted_formats.includes(format)}
                  onChange={(event) => {
                    const next = event.target.checked
                      ? [...form.accepted_formats, format]
                      : form.accepted_formats.filter((item) => item !== format);
                    update("accepted_formats", next);
                  }}
                />
                {format}
              </label>
            ))}
          </div>
          {errorFor("accepted_formats", serverErrors) ? <p className="mt-1 text-sm text-red-700">{errorFor("accepted_formats", serverErrors)}</p> : null}
        </fieldset>
        <Field label="Maximum size (MB)" help="1 to 5 megabytes." error={errorFor("max_size_mb", serverErrors)}>
          <input
            className="field"
            type="number"
            min={1}
            max={5}
            value={form.max_size_mb}
            onChange={(event) => update("max_size_mb", Number(event.target.value))}
          />
        </Field>
        <Field label="Validity (days)" help="Leave empty if the document does not expire. 1–3650 days otherwise." error={errorFor("validity_days", serverErrors)}>
          <input
            className="field"
            type="number"
            min={1}
            max={3650}
            value={form.validity_days ?? ""}
            onChange={(event) => update("validity_days", event.target.value === "" ? null : Number(event.target.value))}
          />
        </Field>
        <TagInput
          label="English keywords"
          help="Words that should appear on this document. Used to guess the document type."
          values={form.keywords.en}
          error={errorFor("keywords.en", serverErrors) || errorFor("keywords", serverErrors)}
          onAdd={(word) => addKeyword("en", word)}
          onRemove={(word) => update("keywords", { ...form.keywords, en: form.keywords.en.filter((item) => item !== word) })}
        />
        <TagInput
          label="Tamil keywords"
          values={form.keywords.ta}
          error={errorFor("keywords.ta", serverErrors)}
          onAdd={(word) => addKeyword("ta", word)}
          onRemove={(word) => update("keywords", { ...form.keywords, ta: form.keywords.ta.filter((item) => item !== word) })}
        />
        <fieldset className="mt-4">
          <legend className="text-sm font-medium text-navy">Required fields</legend>
          <div className="mt-2 flex flex-wrap gap-3">
            {REQUIRED_FIELD_OPTIONS.map((option) => (
              <label key={option.id} className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={form.required_fields.includes(option.id)}
                  onChange={(event) => {
                    const next = event.target.checked
                      ? [...form.required_fields, option.id]
                      : form.required_fields.filter((item) => item !== option.id);
                    update("required_fields", next);
                  }}
                />
                {option.label}
              </label>
            ))}
          </div>
        </fieldset>
        <button type="button" className="btn-secondary mt-4" onClick={applyPhotoPreset}>
          Photo-type document (no text checks)
        </button>
        {photoType ? <p className="mt-2 text-sm text-muted">Photo-type: keywords and required fields are empty, so ID pattern and name matching stay off.</p> : null}
        <h3 className="mt-6 text-lg font-semibold text-navy">Quality rules</h3>
        <div className="grid gap-3 sm:grid-cols-2">
          <NumberRule label="Minimum width (px)" value={form.rules.min_width} error={errorFor("rules.min_width", serverErrors)} onChange={(value) => setForm((current) => ({ ...current, rules: { ...current.rules, min_width: value } }))} />
          <NumberRule label="Minimum height (px)" value={form.rules.min_height} error={errorFor("rules.min_height", serverErrors)} onChange={(value) => setForm((current) => ({ ...current, rules: { ...current.rules, min_height: value } }))} />
          <NumberRule label="Minimum sharpness" value={form.rules.min_blur_score} error={errorFor("rules.min_blur_score", serverErrors)} onChange={(value) => setForm((current) => ({ ...current, rules: { ...current.rules, min_blur_score: value } }))} />
          <NumberRule label="Minimum brightness" value={form.rules.min_brightness} error={errorFor("rules.min_brightness", serverErrors)} onChange={(value) => setForm((current) => ({ ...current, rules: { ...current.rules, min_brightness: value } }))} />
          <NumberRule label="Maximum brightness" value={form.rules.max_brightness} error={errorFor("rules.max_brightness", serverErrors)} onChange={(value) => setForm((current) => ({ ...current, rules: { ...current.rules, max_brightness: value } }))} />
          <NumberRule label="Maximum age (days)" value={form.rules.max_age_days} error={errorFor("rules.max_age_days", serverErrors)} onChange={(value) => setForm((current) => ({ ...current, rules: { ...current.rules, max_age_days: value } }))} />
        </div>
        <Field
          label="ID number pattern"
          help="Python regular expression, for example ^[0-9]{12}$. Nested patterns such as (a+)+ are rejected."
          error={errorFor("rules.id_number_pattern", serverErrors) || errorFor("form", serverErrors)}
        >
          <input
            className="field"
            value={form.rules.id_number_pattern ?? ""}
            disabled={photoType}
            onChange={(event) => setForm((current) => ({ ...current, rules: { ...current.rules, id_number_pattern: event.target.value || null } }))}
          />
        </Field>
        <div className="mt-2 flex flex-col gap-2 sm:flex-row">
          <input className="field" value={sample} onChange={(event) => setSample(event.target.value)} aria-label="Sample text for the ID pattern" />
          <button
            type="button"
            className="btn-secondary"
            onClick={() => setPatternNote(testPattern(form.rules.id_number_pattern ?? "", sample))}
          >
            Test pattern
          </button>
        </div>
        {patternNote ? <p className="mt-1 text-sm text-muted">{patternNote}</p> : null}
        <label className="mt-4 flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={form.rules.check_name_match === true}
            disabled={photoType}
            onChange={(event) => setForm((current) => ({ ...current, rules: { ...current.rules, check_name_match: event.target.checked } }))}
          />
          Compare name with other documents
        </label>
        {serverErrors.length > 0 ? (
          <ul className="mt-4 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-800">
            {serverErrors.map((item) => (
              <li key={`${item.field}-${item.message}`}>
                {item.field}: {item.message}
              </li>
            ))}
          </ul>
        ) : null}
        <div className="mt-6 flex flex-wrap gap-2">
          <button type="submit" className="btn-primary" disabled={busy}>
            {busy ? "Saving..." : "Save document"}
          </button>
          <button type="button" className="btn-secondary" onClick={onCancel} disabled={busy}>
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}

function Field({
  label,
  help,
  error,
  children,
}: {
  label: string;
  help?: string;
  error?: string | null;
  children: ReactNode;
}) {
  return (
    <label className="mt-4 block text-sm font-medium text-navy">
      {label}
      {help ? <span className="block font-normal text-muted">{help}</span> : null}
      {children}
      {error ? <span className="mt-1 block font-normal text-red-700">{error}</span> : null}
    </label>
  );
}

function NumberRule({
  label,
  value,
  error,
  onChange,
}: {
  label: string;
  value: number | null | undefined;
  error?: string | null;
  onChange: (value: number | null) => void;
}) {
  return (
    <label className="text-sm font-medium text-navy">
      {label}
      <input className="field" type="number" value={value ?? ""} onChange={(event) => onChange(event.target.value === "" ? null : Number(event.target.value))} />
      {error ? <span className="mt-1 block font-normal text-red-700">{error}</span> : null}
    </label>
  );
}

function TagInput({
  label,
  help,
  values,
  error,
  onAdd,
  onRemove,
}: {
  label: string;
  help?: string;
  values: string[];
  error?: string | null;
  onAdd: (word: string) => void;
  onRemove: (word: string) => void;
}) {
  const [draft, setDraft] = useState("");
  return (
    <div className="mt-4">
      <p className="text-sm font-medium text-navy">{label}</p>
      {help ? <p className="text-sm text-muted">{help}</p> : null}
      <div className="mt-2 flex flex-wrap gap-2">
        {values.map((word) => (
          <button key={word} type="button" className="rounded-full bg-sky px-3 py-1 text-sm" onClick={() => onRemove(word)}>
            {word} ×
          </button>
        ))}
      </div>
      <div className="mt-2 flex gap-2">
        <input
          className="field"
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              event.preventDefault();
              onAdd(draft);
              setDraft("");
            }
          }}
        />
        <button
          type="button"
          className="btn-secondary"
          onClick={() => {
            onAdd(draft);
            setDraft("");
          }}
        >
          Add
        </button>
      </div>
      {error ? <p className="mt-1 text-sm text-red-700">{error}</p> : null}
    </div>
  );
}
