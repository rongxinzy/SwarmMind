import type { Message } from "@langchain/langgraph-sdk"

export interface TokenUsage {
  inputTokens: number
  outputTokens: number
  totalTokens: number
}

function usageFromMessage(message: Message): TokenUsage | null {
  if (message.type !== "ai") {
    return null
  }

  const usage = (message as Record<string, unknown>).usage_metadata as
    | {
        input_tokens?: number
        output_tokens?: number
        total_tokens?: number
      }
    | undefined

  if (!usage) {
    return null
  }

  return {
    inputTokens: usage.input_tokens ?? 0,
    outputTokens: usage.output_tokens ?? 0,
    totalTokens: usage.total_tokens ?? 0,
  }
}

export function accumulateUsage(messages: Message[]): TokenUsage | null {
  const total: TokenUsage = {
    inputTokens: 0,
    outputTokens: 0,
    totalTokens: 0,
  }
  let hasUsage = false

  for (const message of messages) {
    const usage = usageFromMessage(message)
    if (!usage) {
      continue
    }
    hasUsage = true
    total.inputTokens += usage.inputTokens
    total.outputTokens += usage.outputTokens
    total.totalTokens += usage.totalTokens
  }

  return hasUsage ? total : null
}

export function formatTokenCount(count: number) {
  if (count < 10_000) {
    return count.toLocaleString()
  }
  return `${(count / 1000).toFixed(1)}K`
}
