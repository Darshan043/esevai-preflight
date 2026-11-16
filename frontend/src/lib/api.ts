// Talks to the FastAPI backend. The URL comes from the frontend env file.

export type HealthResponse = {
  status: string;
  service: string;
  version: string;
  environment: string;
  time: string;
};

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

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
    throw new Error("The backend is not reachable. Start it on port 8000 and try again.");
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
    throw new Error("The backend is not reachable. Start it on port 8000 and try again.");
  }

  if (!response.ok) {
    throw new Error(`The backend returned status ${response.status}.`);
  }

  return (await response.json()) as HealthResponse;
}
