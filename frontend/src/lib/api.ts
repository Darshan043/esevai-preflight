// Talks to the FastAPI backend. The URL comes from the frontend env file.

import type { AiAdvice } from "@/lib/ai";
import { DEFAULT_TIMEOUT_MS, LONG_TIMEOUT_MS, TIMEOUT_ERROR, mapApiError, newRequestId, redirectToLogin } from "@/lib/api-errors";
import type {
  AdminChecksPage,
  AdminDocument,
  AdminDocumentInput,
  AdminFieldError,
  AdminService,
  AdminServiceDetail,
  AdminServiceInput,
  AdminStats,
  PreviewLink,
  PublicUpload,
  ReadinessReport,
  ReportPayload,
  ValidationResult,
} from "@/lib/types";

export type DocumentResult = {
  id: string;
  status: PublicUpload["status"];
  quality_metrics: Record<string, unknown>;
  ocr_text_masked: string | null;
  updated_at: string;
};

export type ValidationSummary = {
  pass: number;
  warning: number;
  fail: number;
};

export type ValidationPayload = {
  application_id: string;
  results: ValidationResult[];
  summary: ValidationSummary;
};

export type HealthResponse = {
  status: string;
  service: string;
  version: string;
  environment: string;
  time: string;
};

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const NETWORK_ERROR = "Cannot reach the server. Is the backend running?";

export type MeResponse = {
  user_id: string;
  email: string | null;
  full_name: string | null;
  role: string;
  preferred_language: string | null;
};

export type AdminPingResponse = {
  ok: boolean;
  message: string;
};

export class ApiError extends Error {
  status: number;
  body: Record<string, unknown> | null;
  fieldErrors: AdminFieldError[];
  requestId: string | null;
  code: string | null;

  constructor(
    status: number,
    message: string,
    body: Record<string, unknown> | null = null,
    fieldErrors: AdminFieldError[] = [],
    requestId: string | null = null,
    code: string | null = null,
  ) {
    super(message);
    this.status = status;
    this.body = body;
    this.fieldErrors = fieldErrors;
    this.requestId = requestId;
    this.code = code;
  }
}

function failFrom(status: number, body: Record<string, unknown> | null): ApiError {
  const mapped = mapApiError(status, body);
  if (status === 401) {
    redirectToLogin();
    return new ApiError(401, "Please sign in again.", body, mapped.fields, mapped.requestId, mapped.code);
  }
  return new ApiError(status, mapped.message, body, mapped.fields, mapped.requestId, mapped.code);
}

type TimedInit = RequestInit & { timeoutMs?: number };

function mergeAbort(timeoutMs: number, external?: AbortSignal | null): { signal: AbortSignal; cancel: () => void } {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  const onAbort = () => controller.abort();
  if (external) {
    if (external.aborted) {
      controller.abort();
    } else {
      external.addEventListener("abort", onAbort, { once: true });
    }
  }
  return {
    signal: controller.signal,
    cancel: () => {
      clearTimeout(timer);
      external?.removeEventListener("abort", onAbort);
    },
  };
}

async function once(path: string, init: TimedInit, accessToken?: string): Promise<Response> {
  const headers = new Headers(init.headers);
  if (accessToken) {
    headers.set("Authorization", `Bearer ${accessToken}`);
  }
  if (!headers.has("X-Request-ID")) {
    headers.set("X-Request-ID", newRequestId());
  }
  const timeoutMs = init.timeoutMs ?? DEFAULT_TIMEOUT_MS;
  const gated = mergeAbort(timeoutMs, init.signal);
  try {
    return await fetch(`${API_URL}${path}`, { ...init, headers, signal: gated.signal });
  } catch (caught) {
    if (caught instanceof DOMException && caught.name === "AbortError") {
      if (init.signal?.aborted) {
        throw caught;
      }
      throw new Error(TIMEOUT_ERROR);
    }
    throw new Error(NETWORK_ERROR);
  } finally {
    gated.cancel();
  }
}

async function rawRequest(path: string, init: TimedInit, accessToken?: string): Promise<Response> {
  const method = (init.method ?? "GET").toUpperCase();
  try {
    return await once(path, init, accessToken);
  } catch (caught) {
    if (method === "GET" && caught instanceof Error && caught.message === NETWORK_ERROR) {
      return once(path, init, accessToken);
    }
    throw caught;
  }
}

export async function fetchWithToken<T>(path: string, accessToken: string): Promise<T> {
  // Sends the Supabase access token. The backend checks it and loads the role.
  const response = await rawRequest(path, { method: "GET" }, accessToken);
  const body = await readBody(response);
  if (!response.ok) {
    throw failFrom(response.status, body);
  }
  return body as T;
}

export async function getHealth(): Promise<HealthResponse> {
  const response = await rawRequest("/health", { method: "GET" });
  const body = await readBody(response);
  if (!response.ok) {
    throw failFrom(response.status, body);
  }
  return body as HealthResponse;
}

async function authRequest(path: string, accessToken: string, init: TimedInit): Promise<Response> {
  return rawRequest(path, init, accessToken);
}

export function uploadUrl(applicationId: string, requiredDocumentId: string): string {
  return `${API_URL}/applications/${applicationId}/documents/${requiredDocumentId}`;
}

export async function fetchPreviewUrl(documentId: string, accessToken: string): Promise<PreviewLink> {
  const response = await authRequest(`/documents/${documentId}/preview-url`, accessToken, { method: "GET" });
  const body = await readBody(response);
  if (!response.ok) {
    throw failFrom(response.status, body);
  }
  return body as PreviewLink;
}

export async function deleteUploadedDocument(documentId: string, accessToken: string): Promise<void> {
  const response = await authRequest(`/documents/${documentId}`, accessToken, { method: "DELETE" });
  if (!response.ok) {
    throw failFrom(response.status, await readBody(response));
  }
}

async function readBody(response: Response): Promise<Record<string, unknown>> {
  try {
    const body = (await response.json()) as unknown;
    if (body && typeof body === "object") {
      return body as Record<string, unknown>;
    }
  } catch {
    // The body was not JSON.
  }
  return {};
}

function isDocumentResult(value: Record<string, unknown>): value is DocumentResult {
  return typeof value.id === "string" && typeof value.status === "string";
}

async function readDocumentResult(response: Response): Promise<DocumentResult> {
  const body = await readBody(response);
  if (!response.ok) {
    throw failFrom(response.status, body);
  }
  if (!isDocumentResult(body)) {
    throw new Error("The server response could not be read.");
  }
  return {
    id: body.id,
    status: body.status,
    quality_metrics: body.quality_metrics && typeof body.quality_metrics === "object" ? body.quality_metrics : {},
    ocr_text_masked: typeof body.ocr_text_masked === "string" ? body.ocr_text_masked : null,
    updated_at: typeof body.updated_at === "string" ? body.updated_at : "",
  };
}

export async function processDocument(
  documentId: string,
  accessToken: string,
  signal?: AbortSignal,
): Promise<DocumentResult> {
  const response = await authRequest(`/documents/${documentId}/process`, accessToken, {
    method: "POST",
    signal,
    timeoutMs: LONG_TIMEOUT_MS,
  });
  return readDocumentResult(response);
}

export async function fetchDocumentResult(documentId: string, accessToken: string): Promise<DocumentResult> {
  const response = await authRequest(`/documents/${documentId}/result`, accessToken, { method: "GET" });
  return readDocumentResult(response);
}

function isValidationPayload(value: Record<string, unknown>): value is ValidationPayload {
  return typeof value.application_id === "string" && Array.isArray(value.results) && !!value.summary && typeof value.summary === "object";
}

async function readValidation(response: Response): Promise<ValidationPayload> {
  const body = await readBody(response);
  if (!response.ok) {
    throw failFrom(response.status, body);
  }
  if (!isValidationPayload(body)) {
    throw new Error("The server response could not be read.");
  }
  const summary = body.summary as ValidationSummary;
  return {
    application_id: body.application_id,
    results: body.results as ValidationResult[],
    summary: {
      pass: Number(summary.pass) || 0,
      warning: Number(summary.warning) || 0,
      fail: Number(summary.fail) || 0,
    },
  };
}

export async function extractDocument(
  documentId: string,
  accessToken: string,
  force = false,
): Promise<Record<string, unknown>> {
  const suffix = force ? "?force=true" : "";
  const response = await authRequest(`/documents/${documentId}/extract${suffix}`, accessToken, {
    method: "POST",
    timeoutMs: LONG_TIMEOUT_MS,
  });
  const body = await readBody(response);
  if (!response.ok) {
    throw failFrom(response.status, body);
  }
  return body;
}

export async function explainApplication(
  applicationId: string,
  accessToken: string,
  language: "en" | "ta",
): Promise<AiAdvice> {
  const response = await authRequest(`/applications/${applicationId}/explain`, accessToken, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ language }),
    timeoutMs: LONG_TIMEOUT_MS,
  });
  return readAdvice(response);
}

export async function fetchAiAdvice(applicationId: string, accessToken: string): Promise<AiAdvice | null> {
  const response = await authRequest(`/applications/${applicationId}/ai-advice`, accessToken, { method: "GET" });
  if (response.status === 200 && (await response.clone().text()) === "null") {
    return null;
  }
  return readAdvice(response);
}

async function readAdvice(response: Response): Promise<AiAdvice> {
  const body = await readBody(response);
  if (!response.ok) {
    throw failFrom(response.status, body);
  }
  const items = Array.isArray(body.items)
    ? body.items.filter(
        (item): item is { id: string; explanation: string } =>
          !!item && typeof item === "object" && typeof (item as { id?: unknown }).id === "string" && typeof (item as { explanation?: unknown }).explanation === "string",
      )
    : [];
  return {
    language: typeof body.language === "string" ? body.language : null,
    generated_at: typeof body.generated_at === "string" ? body.generated_at : null,
    model: typeof body.model === "string" ? body.model : null,
    items,
    overall_tip: typeof body.overall_tip === "string" ? body.overall_tip : null,
  };
}

export async function validateApplication(applicationId: string, accessToken: string): Promise<ValidationPayload> {
  const response = await authRequest(`/applications/${applicationId}/validate`, accessToken, { method: "POST" });
  return readValidation(response);
}

export async function fetchValidation(applicationId: string, accessToken: string): Promise<ValidationPayload> {
  const response = await authRequest(`/applications/${applicationId}/validation`, accessToken, { method: "GET" });
  return readValidation(response);
}

function isReadinessReport(value: unknown): value is ReadinessReport {
  if (!value || typeof value !== "object") {
    return false;
  }
  const row = value as Partial<ReadinessReport>;
  return typeof row.score === "number" && typeof row.label === "string" && Array.isArray(row.next_steps);
}

async function readReportBody(response: Response): Promise<ReadinessReport> {
  const body = await readBody(response);
  if (!response.ok) {
    throw failFrom(response.status, body);
  }
  if (!isReadinessReport(body)) {
    throw new Error("The server response could not be read.");
  }
  return body;
}

export async function generateReport(applicationId: string, accessToken: string): Promise<ReadinessReport> {
  const response = await authRequest(`/applications/${applicationId}/report`, accessToken, { method: "POST" });
  return readReportBody(response);
}

export async function fetchReport(applicationId: string, accessToken: string): Promise<ReportPayload> {
  const response = await authRequest(`/applications/${applicationId}/report`, accessToken, { method: "GET" });
  const body = await readBody(response);
  if (!response.ok) {
    throw failFrom(response.status, body);
  }
  const report = isReadinessReport(body.report) ? body.report : null;
  return { report, is_current: body.is_current === true && report !== null };
}

export async function deleteApplicationOnServer(applicationId: string, accessToken: string): Promise<void> {
  const response = await authRequest(`/applications/${applicationId}`, accessToken, { method: "DELETE" });
  if (!response.ok) {
    throw failFrom(response.status, await readBody(response));
  }
}

async function adminRequest<T>(path: string, accessToken: string, init: TimedInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    ...(init.body ? { "Content-Type": "application/json" } : {}),
  };
  const response = await authRequest(path, accessToken, { ...init, headers: { ...headers, ...(init.headers as Record<string, string> | undefined) } });
  if (response.status === 204) {
    return undefined as T;
  }
  const body = await readBody(response);
  if (response.status === 403) {
    const mapped = mapApiError(403, body);
    throw new ApiError(403, "Access denied.", body, mapped.fields, mapped.requestId, mapped.code);
  }
  if (!response.ok) {
    throw failFrom(response.status, body);
  }
  return body as T;
}

export type CleanupSummary = {
  dry_run: boolean;
  days: number;
  applications: number;
  files: number;
  deleted_applications: number;
  deleted_files: number;
  skipped_applications: number;
};

export async function runAdminCleanup(accessToken: string, dryRun = true): Promise<CleanupSummary> {
  return adminRequest<CleanupSummary>("/admin/cleanup", accessToken, {
    method: "POST",
    body: JSON.stringify({ dry_run: dryRun }),
  });
}

export async function fetchAdminStats(accessToken: string, days: number): Promise<AdminStats> {
  return adminRequest<AdminStats>(`/admin/stats?days=${days}`, accessToken);
}

export async function fetchAdminChecks(accessToken: string, page = 1, pageSize = 20): Promise<AdminChecksPage> {
  return adminRequest<AdminChecksPage>(`/admin/applications?page=${page}&page_size=${pageSize}`, accessToken);
}

export async function fetchAdminServices(accessToken: string): Promise<{ items: AdminService[] }> {
  return adminRequest<{ items: AdminService[] }>("/admin/services", accessToken);
}

export async function fetchAdminService(accessToken: string, serviceId: string): Promise<AdminServiceDetail> {
  return adminRequest<AdminServiceDetail>(`/admin/services/${serviceId}`, accessToken);
}

export async function createAdminService(accessToken: string, payload: AdminServiceInput): Promise<AdminService> {
  return adminRequest<AdminService>("/admin/services", accessToken, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateAdminService(accessToken: string, serviceId: string, payload: AdminServiceInput): Promise<AdminService> {
  return adminRequest<AdminService>(`/admin/services/${serviceId}`, accessToken, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export async function duplicateAdminService(
  accessToken: string,
  serviceId: string,
  payload: { new_slug: string; new_name_en: string },
): Promise<{ service: AdminService; documents: AdminDocument[] }> {
  return adminRequest(`/admin/services/${serviceId}/duplicate`, accessToken, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function deleteAdminService(accessToken: string, serviceId: string): Promise<void> {
  await adminRequest<void>(`/admin/services/${serviceId}`, accessToken, { method: "DELETE" });
}

export async function createAdminDocument(accessToken: string, serviceId: string, payload: AdminDocumentInput): Promise<AdminDocument> {
  return adminRequest<AdminDocument>(`/admin/services/${serviceId}/documents`, accessToken, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateAdminDocument(accessToken: string, documentId: string, payload: AdminDocumentInput): Promise<AdminDocument> {
  return adminRequest<AdminDocument>(`/admin/documents/${documentId}`, accessToken, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export async function deleteAdminDocument(accessToken: string, documentId: string): Promise<void> {
  await adminRequest<void>(`/admin/documents/${documentId}`, accessToken, { method: "DELETE" });
}

export async function reorderAdminDocuments(accessToken: string, serviceId: string, ids: string[]): Promise<{ items: AdminDocument[] }> {
  return adminRequest(`/admin/services/${serviceId}/documents/reorder`, accessToken, {
    method: "POST",
    body: JSON.stringify({ ids }),
  });
}

export function isPublicUpload(value: unknown): value is PublicUpload {
  if (!value || typeof value !== "object") {
    return false;
  }
  const row = value as Partial<PublicUpload>;
  return typeof row.id === "string" && typeof row.required_document_id === "string";
}
