// Talks to the FastAPI backend. The URL comes from the frontend env file.

import type { AiAdvice } from "@/lib/ai";
import type { PreviewLink, PublicUpload, ValidationResult } from "@/lib/types";

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

  constructor(status: number, message: string, body: Record<string, unknown> | null = null) {
    super(message);
    this.status = status;
    this.body = body;
  }
}

export async function fetchWithToken<T>(path: string, accessToken: string): Promise<T> {
  // Sends the Supabase access token. The backend checks it and loads the role.
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      headers: { Authorization: `Bearer ${accessToken}` },
    });
  } catch {
    throw new Error(NETWORK_ERROR);
  }

  if (response.status === 401) {
    // Callers send the browser to /login. This file is not a React component.
    throw new ApiError(401, "Please sign in again.");
  }

  if (!response.ok) {
    throw new Error(`The backend returned status ${response.status}.`);
  }

  return (await response.json()) as T;
}

export async function getHealth(): Promise<HealthResponse> {
  let response: Response;

  try {
    response = await fetch(`${API_URL}/health`);
  } catch {
    throw new Error(NETWORK_ERROR);
  }

  if (!response.ok) {
    throw new Error(`The backend returned status ${response.status}.`);
  }

  return (await response.json()) as HealthResponse;
}

async function authRequest(path: string, accessToken: string, init: RequestInit): Promise<Response> {
  try {
    return await fetch(`${API_URL}${path}`, {
      ...init,
      headers: {
        Authorization: `Bearer ${accessToken}`,
        ...(init.headers ?? {}),
      },
    });
  } catch (caught) {
    if (caught instanceof DOMException && caught.name === "AbortError") {
      throw caught;
    }
    throw new Error(NETWORK_ERROR);
  }
}

async function readError(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: string };
    if (typeof body.detail === "string" && body.detail) {
      return body.detail;
    }
  } catch {
    // The body was not JSON. Use the status line below.
  }
  return `The backend returned status ${response.status}.`;
}

export function uploadUrl(applicationId: string, requiredDocumentId: string): string {
  return `${API_URL}/applications/${applicationId}/documents/${requiredDocumentId}`;
}

export async function fetchPreviewUrl(documentId: string, accessToken: string): Promise<PreviewLink> {
  const response = await authRequest(`/documents/${documentId}/preview-url`, accessToken, { method: "GET" });
  if (response.status === 401) {
    throw new ApiError(401, "Please sign in again.");
  }
  if (!response.ok) {
    throw new ApiError(response.status, await readError(response));
  }
  return (await response.json()) as PreviewLink;
}

export async function deleteUploadedDocument(documentId: string, accessToken: string): Promise<void> {
  const response = await authRequest(`/documents/${documentId}`, accessToken, { method: "DELETE" });
  if (response.status === 401) {
    throw new ApiError(401, "Please sign in again.");
  }
  if (!response.ok) {
    throw new ApiError(response.status, await readError(response));
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
  if (response.status === 401) {
    throw new ApiError(401, "Please sign in again.", body);
  }
  const detail = typeof body.detail === "string" ? body.detail : "";
  if (!response.ok) {
    throw new ApiError(response.status, detail || `The backend returned status ${response.status}.`, body);
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
  if (response.status === 401) {
    throw new ApiError(401, "Please sign in again.", body);
  }
  const detail = typeof body.detail === "string" ? body.detail : "";
  if (!response.ok) {
    throw new ApiError(response.status, detail || `The backend returned status ${response.status}.`, body);
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
  const response = await authRequest(`/documents/${documentId}/extract${suffix}`, accessToken, { method: "POST" });
  const body = await readBody(response);
  if (response.status === 401) {
    throw new ApiError(401, "Please sign in again.", body);
  }
  const detail = typeof body.detail === "string" ? body.detail : "";
  if (!response.ok) {
    throw new ApiError(response.status, detail || `The backend returned status ${response.status}.`, body);
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
  if (response.status === 401) {
    throw new ApiError(401, "Please sign in again.", body);
  }
  const detail = typeof body.detail === "string" ? body.detail : "";
  if (!response.ok) {
    throw new ApiError(response.status, detail || `The backend returned status ${response.status}.`, body);
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

export async function deleteApplicationOnServer(applicationId: string, accessToken: string): Promise<void> {
  const response = await authRequest(`/applications/${applicationId}`, accessToken, { method: "DELETE" });
  if (response.status === 401) {
    throw new ApiError(401, "Please sign in again.");
  }
  if (!response.ok) {
    throw new ApiError(response.status, await readError(response));
  }
}

export function isPublicUpload(value: unknown): value is PublicUpload {
  if (!value || typeof value !== "object") {
    return false;
  }
  const row = value as Partial<PublicUpload>;
  return typeof row.id === "string" && typeof row.required_document_id === "string";
}
