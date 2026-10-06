import type {
  AgentEvent,
  ChatReply,
  DatasetProfile,
  Experiment,
  FinalReport,
  PredictionResponse,
  Project,
  RunStatus,
} from "./types";

export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function toError(res: Response): Promise<Error> {
  let detail = `${res.status} ${res.statusText}`;
  try {
    const body: unknown = await res.json();
    if (body && typeof body === "object" && "detail" in body) {
      const d = (body as { detail: unknown }).detail;
      detail = typeof d === "string" ? d : JSON.stringify(d);
    }
  } catch {
    // keep status text
  }
  return new Error(detail);
}

export function csrfToken(): string {
  if (typeof document === "undefined") return "";
  return (
    document.cookie
      .split("; ")
      .find((v) => v.startsWith("mlution_csrf="))
      ?.split("=")[1] ?? ""
  );
}

let refreshing: Promise<Response> | null = null;

export async function request<T>(
  path: string,
  init?: RequestInit,
  retried = false,
): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    credentials: "include",
    headers: {
      ...(init?.body instanceof FormData
        ? {}
        : { "Content-Type": "application/json" }),
      "X-CSRF-Token": csrfToken(),
      ...init?.headers,
    },
  });
  if (
    res.status === 401 &&
    !retried &&
    !path.match(/\/auth\/(login|register|refresh|demo)/)
  ) {
    refreshing ??= fetch(`${API_BASE}/api/auth/refresh`, {
      method: "POST",
      credentials: "include",
      headers: { "X-CSRF-Token": csrfToken() },
    }).finally(() => {
      refreshing = null;
    });
    const refresh = await refreshing;
    if (refresh.ok) return request<T>(path, init, true);
  }
  if (!res.ok) {
    const error = await toError(res);
    if (init?.method && init.method !== "GET" && typeof window !== "undefined")
      window.dispatchEvent(
        new CustomEvent("mlution:toast", {
          detail: { message: error.message, error: true },
        }),
      );
    throw error;
  }
  if (init?.method && init.method !== "GET" && typeof window !== "undefined") {
    const messages: Record<string, string> = {
      projects: "Project saved",
      run: "Run queued",
      predict: "Prediction ready",
      dataset: "Dataset updated",
      cancel: "Cancellation requested",
      "change-password": "Password changed",
      logout: "Signed out",
    };
    const message = messages[path.split("/").pop() ?? ""];
    if (message)
      window.dispatchEvent(
        new CustomEvent("mlution:toast", { detail: { message } }),
      );
  }
  return (await res.json()) as T;
}

export interface User {
  id: string;
  email: string;
  role: "user" | "admin";
}
export const getMe = () => request<User>("/api/auth/me");
export const signOut = () => request("/api/auth/logout", { method: "POST" });
export const authenticate = (
  mode: "login" | "register",
  email: string,
  password: string,
) =>
  request<User>(`/api/auth/${mode}`, {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
export const demoLogin = () =>
  request<User>("/api/auth/demo", { method: "POST" });
export const getRuns = (id: string) =>
  request<{ id: string; status: string }[]>(`/api/projects/${id}/runs`);
export const cancelRun = (id: string, runId: string) =>
  request(`/api/projects/${id}/runs/${runId}/cancel`, { method: "POST" });

export function getHealth(): Promise<{ status: string }> {
  return request("/api/health");
}

export function listProjects(): Promise<Project[]> {
  return request("/api/projects");
}

export interface CreateProjectInput {
  name: string;
  description: string;
  use_demo_dataset: boolean;
  target_column: string | null;
  primary_metric: string | null;
}

export function createProject(input: CreateProjectInput): Promise<Project> {
  return request("/api/projects", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function getProject(id: string): Promise<Project> {
  return request(`/api/projects/${id}`);
}

export function uploadDataset(id: string, file: File): Promise<DatasetProfile> {
  const form = new FormData();
  form.append("file", file);
  return request(`/api/projects/${id}/dataset`, { method: "POST", body: form });
}

export function uploadDemoDataset(id: string): Promise<DatasetProfile> {
  const form = new FormData();
  form.append("demo", "true");
  return request(`/api/projects/${id}/dataset`, { method: "POST", body: form });
}

export interface RunProjectInput {
  target_column: string | null;
  primary_metric: string | null;
  business_priority: string | null;
  time_budget_seconds: number;
  max_experiments: number;
}

export function runProject(
  id: string,
  input: RunProjectInput,
): Promise<{ status: string; project_id: string }> {
  return request(`/api/projects/${id}/run`, {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function getStatus(id: string): Promise<RunStatus> {
  return request(`/api/projects/${id}/status`);
}

export function getEvents(id: string, afterId = 0): Promise<AgentEvent[]> {
  return request(`/api/projects/${id}/events?after_id=${afterId}`);
}

export function getProfile(id: string): Promise<DatasetProfile> {
  return request(`/api/projects/${id}/profile`);
}

export function getExperiments(id: string): Promise<Experiment[]> {
  return request(`/api/projects/${id}/experiments`);
}

export function getReport(id: string): Promise<FinalReport> {
  return request(`/api/projects/${id}/report`);
}

export function predict(
  id: string,
  features: Record<string, unknown>,
): Promise<PredictionResponse> {
  return request(`/api/projects/${id}/predict`, {
    method: "POST",
    body: JSON.stringify({ features }),
  });
}

export function sendChat(id: string, message: string): Promise<ChatReply> {
  return request(`/api/projects/${id}/chat`, {
    method: "POST",
    body: JSON.stringify({ message }),
  });
}

export function eventsStreamUrl(id: string): string {
  return `${API_BASE}/api/projects/${id}/events/stream`;
}

export function modelDownloadUrl(id: string): string {
  return `${API_BASE}/api/projects/${id}/model`;
}

export function codeDownloadUrl(id: string): string {
  return `${API_BASE}/api/projects/${id}/code`;
}
