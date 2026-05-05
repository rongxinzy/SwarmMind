import { getBackendBaseURL } from "../config";
import type { AgentThread } from "../threads";

function encodeArtifactPath(filepath: string) {
  return filepath.split("/").map(encodeURIComponent).join("/");
}

function withLeadingSlash(path: string) {
  return path.startsWith("/") ? path : `/${path}`;
}

export function urlOfArtifact({
  filepath,
  threadId,
  download = false,
  isMock = false,
}: {
  filepath: string;
  threadId: string;
  download?: boolean;
  isMock?: boolean;
}) {
  const encodedPath = withLeadingSlash(encodeArtifactPath(filepath));
  if (isMock) {
    return `${getBackendBaseURL()}/mock/api/threads/${threadId}/artifacts${encodedPath}${download ? "?download=true" : ""}`;
  }
  return `${getBackendBaseURL()}/api/threads/${threadId}/artifacts${encodedPath}${download ? "?download=true" : ""}`;
}

export function extractArtifactsFromThread(thread: AgentThread) {
  return thread.values.artifacts ?? [];
}

export function resolveArtifactURL(absolutePath: string, conversationId: string) {
  return `${getBackendBaseURL()}/conversations/${conversationId}/artifacts${withLeadingSlash(encodeArtifactPath(absolutePath))}`;
}
