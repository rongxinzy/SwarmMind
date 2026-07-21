import type { ChatMessage, ChatPlanStep, ChatPlanStepStatus } from "@/types/chat"

export function normalizePlanSteps(value: unknown): ChatPlanStep[] {
  if (!Array.isArray(value)) {
    return []
  }

  return value.flatMap((step) => {
    if (!isRecord(step)) {
      return []
    }
    const content = stringValue(step.description) ?? stringValue(step.content)
    if (!content) {
      return []
    }
    return [
      {
        content,
        status: normalizePlanStepStatus(step.status),
      },
    ]
  })
}

export function derivePlanStepsFromMessages(messages: ChatMessage[]): ChatPlanStep[] | null {
  let latest: ChatPlanStep[] | null = null

  for (const message of messages) {
    if (message.type !== "ai") {
      continue
    }

    for (const toolCall of message.tool_calls ?? []) {
      if (toolCall.name !== "write_todos") {
        continue
      }
      const args = isRecord(toolCall.args) ? toolCall.args : {}
      latest = normalizePlanSteps(args.todos)
    }
  }

  return latest
}

function normalizePlanStepStatus(value: unknown): ChatPlanStepStatus {
  if (value === "completed" || value === "in_progress" || value === "pending") {
    return value
  }
  return "pending"
}

function stringValue(value: unknown) {
  return typeof value === "string" && value.trim() ? value.trim() : undefined
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null
}
