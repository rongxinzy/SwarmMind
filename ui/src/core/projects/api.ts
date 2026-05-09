import { consumeNdjsonStream } from "../chat/stream";
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

export interface SendProjectMessageRequest {
  content: string;
  mode?: string;
  model_name?: string | null;
}

/**
 * Stream a project execution turn. Returns a fetch Response so callers can
 * pass its body to consumeNdjsonStream with their own event handler.
 */
export async function streamProjectMessage(
  projectId: string,
  request: SendProjectMessageRequest,
): Promise<Response> {
  const res = await fetch(`/projects/${projectId}/messages/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!res.ok || !res.body) {
    const detail = await res.text().catch(() => res.statusText);
    throw new Error(`HTTP ${res.status}: ${detail}`);
  }
  return res;
}

/**
 * Stream project execution events, calling onEvent for each parsed NDJSON line.
 * Reuses the same stream parser as chat sessions.
 */
export async function consumeProjectStream<T>(
  projectId: string,
  request: SendProjectMessageRequest,
  onEvent: (event: T) => void,
  onParseError?: (rawLine: string, error: unknown) => void,
): Promise<void> {
  const res = await streamProjectMessage(projectId, request);
  await consumeNdjsonStream<T>(res.body!, onEvent, onParseError);
}
