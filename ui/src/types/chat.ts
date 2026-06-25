export type ChatStatus = "ready" | "submitted" | "streaming" | "error"

export interface TextPart {
  type: "text"
  text: string
  state?: "streaming" | "done"
}

export interface ReasoningPart {
  type: "reasoning"
  text: string
  state?: "streaming" | "done"
}

export interface ToolInvocationPart {
  type: "tool-invocation"
  toolCallId: string
  toolName: string
  state: "input-streaming" | "input-available" | "output-available" | "output-error"
  input?: Record<string, unknown>
  output?: Record<string, unknown>
}

export interface ApprovalRequestPart {
  type: "approval-request"
  approvalId: string
  capability: string
  riskTier: string
  runId?: string
  projectId?: string
}

export interface ArtifactPart {
  type: "artifact"
  artifactType?: string
  name?: string
}

export type MessagePart = TextPart | ReasoningPart | ToolInvocationPart | ApprovalRequestPart | ArtifactPart

export interface ChatMessage {
  id: string
  role: "user" | "assistant" | "system"
  content?: string
  parts: MessagePart[]
}
