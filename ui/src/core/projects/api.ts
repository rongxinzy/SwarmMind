import type {
  Project,
  ProjectListResponse,
  ProjectOverviewResponse,
} from "./types";

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, init);
  if (!res.ok) {
    const detail = await res.text().catch(() => res.statusText);
    throw new Error(`HTTP ${res.status}: ${detail}`);
  }
  return res.json() as Promise<T>;
}

export async function listProjects(): Promise<ProjectListResponse> {
  return fetchJson<ProjectListResponse>("/projects");
}

export async function getProject(id: string): Promise<Project> {
  return fetchJson<Project>(`/projects/${id}`);
}

export async function getProjectOverview(id: string): Promise<ProjectOverviewResponse> {
  return fetchJson<ProjectOverviewResponse>(`/projects/${id}/overview`);
}

export async function promoteConversation(
  conversationId: string,
  body?: { title?: string; goal?: string; next_step?: string },
): Promise<Project> {
  return fetchJson<Project>(`/conversations/${conversationId}/promote`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
}
