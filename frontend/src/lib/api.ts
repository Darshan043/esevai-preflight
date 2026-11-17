// Talks to the FastAPI backend. The URL comes from the frontend env file.

import type { PreviewLink, PublicUpload } from "@/lib/types";

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

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
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
  } catch {
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
