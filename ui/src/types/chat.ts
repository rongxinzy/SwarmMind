import type { Message as DeerFlowMessage } from "@langchain/langgraph-sdk"

export type ChatStatus = "ready" | "submitted" | "streaming" | "error"

export type ChatMessage = DeerFlowMessage

export type ChatPlanStepStatus = "pending" | "in_progress" | "completed"

export interface ChatPlanStep {
  content: string
  status: ChatPlanStepStatus
}
