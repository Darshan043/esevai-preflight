import type { AdminFieldError } from "@/lib/types";

export const DEFAULT_TIMEOUT_MS = 30_000;
export const LONG_TIMEOUT_MS = 60_000;
export const TIMEOUT_ERROR = "The request took too long. Please try again.";

export type MappedApiError = {
  message: string;
  code: string | null;
  requestId: string | null;
  fields: AdminFieldError[];
};

function asRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === "object" ? (value as Record<string, unknown>) : null;
}

function parseFields(value: unknown): AdminFieldError[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value
    .map((item) => asRecord(item))
    .filter((item): item is Record<string, unknown> => Boolean(item))
    .filter((item) => typeof item.field === "string" && typeof item.message === "string")
    .map((item) => ({ field: item.field as string, message: item.message as string }));
}

export function mapApiError(status: number, body: Record<string, unknown> | null): MappedApiError {
  const error = asRecord(body?.error);
  if (error && typeof error.message === "string" && error.message.trim()) {
    return {
      message: error.message,
      code: typeof error.code === "string" ? error.code : null,
      requestId: typeof error.request_id === "string" ? error.request_id : null,
      fields: parseFields(error.fields),
    };
  }
  const detail = body?.detail;
  if (typeof detail === "string" && detail.trim()) {
    return {
      message: detail,
      code: null,
      requestId: null,
      fields: [],
    };
  }
  const fields = parseFields(detail);
  if (fields[0]) {
    return {
      message: fields[0].message,
      code: null,
      requestId: null,
      fields,
    };
  }
  return {
    message: `The backend returned status ${status}.`,
    code: null,
    requestId: null,
    fields: [],
  };
}

export function newRequestId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID().replaceAll("-", "").slice(0, 16);
  }
  return `${Date.now().toString(16)}${Math.random().toString(16).slice(2, 10)}`.slice(0, 16);
}

export function redirectToLogin(): void {
  if (typeof window === "undefined") {
    return;
  }
  if (window.location.pathname === "/login") {
    return;
  }
  const next = `${window.location.pathname}${window.location.search}`;
  // This helper is used from fetch, not a React event handler.
  // eslint-disable-next-line @next/next/no-location-assign-relative-destination -- hard navigation after a 401
  window.location.assign(`/login?next=${encodeURIComponent(next)}`);
}
