export interface StoredMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  created_at?: string;
}

export interface RuntimeModelOption {
  name: string;
  provider: string;
  model: string;
  display_name?: string | null;
  description?: string | null;
  supports_vision: boolean;
  is_default: boolean;
}

export interface RuntimeModelCatalogResponse {
  models: RuntimeModelOption[];
  default_model?: string | null;
}

export interface RuntimeActivity {
  id: string;
  label: string;
  status: "running" | "completed";
  detail?: string;
}

export interface RuntimeState {
  phase: "idle" | "accepted" | "routing" | "running" | "completed" | "error";
  label: string;
  activities: RuntimeActivity[];
}

export interface StreamEventUserMessage {
  id: string;
  role: "user";
  content: string;
  created_at?: string;
}

export interface StreamEventAssistantMessage {
  id: string;
  role: "assistant";
  content: string;
  created_at?: string;
}

export type StreamStatus = "thinking" | "running" | "clarification" | "artifact" | null;

export interface StreamStep {
  step: number;
  totalSteps?: number;
}

export type ChatErrorType = "network" | "server" | "timeout" | "unknown";

export interface ChatError {
  type: ChatErrorType;
  message: string;
  retryCount: number;
}

export type StreamEvent =
  | { type: "status"; phase: RuntimeState["phase"]; label: string; step?: number; total_steps?: number }
  | { type: "user_message"; message: StreamEventUserMessage }
  | { type: "thinking"; message_id: string; content: string }
  | { type: "assistant_message"; message_id: string; content: string }
  | { type: "assistant_final"; message: StreamEventAssistantMessage }
  | {
      type: "team_activity";
      activity: {
        id: string;
        label: string;
        status: RuntimeActivity["status"];
        detail?: string | null;
      };
    }
  | { type: "task_started"; task: { id: string; description: string; status: "in_progress" } }
  | { type: "task_running"; task: { id: string; message?: unknown } }
  | { type: "task_completed"; task: { id: string; result?: string; status: "completed" } }
  | { type: "task_failed"; task: { id: string; error?: string; status: "failed" } }
  | { type: "clarification_request"; clarification: { id: string; content: string } }
  | { type: "artifact"; path: string; filename?: string }
  | { type: "status.thinking"; mode?: string; text?: string }
  | { type: "status.running"; step?: number; total_steps?: number }
  | { type: "status.clarification"; question: string }
  | { type: "status.artifact"; name?: string; artifact_type?: string }
  | { type: "content.accumulated"; text: string }
  | {
      type: "title";
      conversation: ConversationRecord;
    }
  | { type: "error"; code?: string; message: string }
  | { type: "done" };

export type ChatMessage = StoredMessage & {
  pendingPersist?: boolean;
  isStreaming?: boolean;
  thinking?: string;
  isReasoningStreaming?: boolean;
};

export type ConversationMode = "flash" | "thinking" | "pro" | "ultra";

export interface ConversationRecord {
  id: string;
  title: string;
  title_status: "pending" | "generated" | "fallback" | "manual";
  updated_at: string;
  created_at: string;
}
