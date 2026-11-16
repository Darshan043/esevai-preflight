// Talks to the FastAPI backend. The URL comes from the frontend env file.

export type HealthResponse = {
  status: string;
  service: string;
  version: string;
  environment: string;
  time: string;
};

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

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
