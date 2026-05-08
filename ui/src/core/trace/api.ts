export interface TraceSummaryResponse {
  steps_count: number;
  subagent_calls_count: number;
  artifacts_count: number;
  blocked_points: string[];
  summary: string;
}

export async function getMessageTrace(
  conversationId: string,
  messageId: string,
): Promise<TraceSummaryResponse> {
  const res = await fetch(
    `/conversations/${conversationId}/messages/${messageId}/trace`,
  );
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }
  return res.json() as Promise<TraceSummaryResponse>;
}
