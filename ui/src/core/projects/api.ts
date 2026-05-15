import { consumeNdjsonStream } from "../chat/stream";
import type {
  ApprovalListResponse,
  AuditLogListResponse,
  Project,
  ProjectListResponse,
  ProjectOverviewResponse,
  RunEvent,
  Task,
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

export async function getRunEvents(projectId: string, runId: string): Promise<RunEvent[]> {
  const data = await fetchJson<AuditLogListResponse>(`/audit-logs?project_id=${projectId}&run_id=${runId}`);
  return data.items;
}

export async function listApprovals(params?: { project_id?: string; status?: string }): Promise<ApprovalListResponse> {
  const qs = new URLSearchParams();
  if (params?.project_id) qs.set("project_id", params.project_id);
  if (params?.status) qs.set("status", params.status);
  const query = qs.toString() ? `?${qs}` : "";
  return fetchJson<ApprovalListResponse>(`/approvals${query}`);
}

export async function patchApproval(approvalId: string, body: { status: string; decision_reason?: string | null }): Promise<void> {
  await fetch(`/approvals/${approvalId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export async function getProjectTasks(projectId: string): Promise<{ items: Task[]; total: number }> {
  return fetchJson<{ items: Task[]; total: number }>(`/projects/${projectId}/tasks`);
}

export async function getProjectAuditLogs(projectId: string): Promise<AuditLogListResponse> {
  return fetchJson<AuditLogListResponse>(`/audit-logs?project_id=${projectId}`);
}
