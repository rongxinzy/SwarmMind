import { useCallback, useEffect, useRef, useState } from "react"
import { apiFetch } from "@/lib/api"
import type { ChatMessage, ChatStatus, MessagePart, TextPart, ReasoningPart, ToolInvocationPart } from "@/types/chat"

interface ChatState {
  messages: ChatMessage[]
  status: ChatStatus
  error: string | null
}

interface UseSwarmChatOptions {
  conversationId?: string
  projectId?: string
  mode?: string
  modelName?: string
  onConversationCreated?: (id: string) => void
}

export function useSwarmChat({
  conversationId,
  projectId,
  mode = "flash",
  modelName,
  onConversationCreated,
}: UseSwarmChatOptions) {
  const [state, setState] = useState<ChatState>({ messages: [], status: "ready", error: null })
  const abortRef = useRef<AbortController | null>(null)

  // Load history when conversationId changes
  useEffect(() => {
    if (!conversationId) {
      setState((prev) => ({ ...prev, messages: [] }))
      return
    }

    let cancelled = false
    async function loadHistory() {
      try {
        const res = await apiFetch(`/api/chat/history?conversation_id=${conversationId}`)
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const data = (await res.json()) as { messages: ChatMessage[] }
        if (!cancelled) {
          setState({ messages: data.messages, status: "ready", error: null })
        }
      } catch (err) {
        if (!cancelled) {
          setState((prev) => ({ ...prev, error: err instanceof Error ? err.message : "加载历史失败" }))
        }
      } finally {
        // no-op
      }
    }
    void loadHistory()
    return () => {
      cancelled = true
    }
  }, [conversationId])

  const stop = useCallback(() => {
    abortRef.current?.abort()
    abortRef.current = null
    setState((prev) => ({ ...prev, status: "ready" }))
  }, [])

  const appendUserMessage = useCallback((text: string) => {
    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      content: text,
      parts: [{ type: "text", text, state: "done" }],
    }
    setState((prev) => ({ ...prev, messages: [...prev.messages, userMessage] }))
    return userMessage
  }, [])

  const sendMessage = useCallback(
    async (text: string, _files?: File[]) => {
      if (!text.trim()) return
      if (state.status === "streaming" || state.status === "submitted") return

      abortRef.current?.abort()
      const abortController = new AbortController()
      abortRef.current = abortController

      const userMessage = appendUserMessage(text)
      const currentMessages = [...state.messages, userMessage]

      setState((prev) => ({ ...prev, status: "submitted", error: null }))

      try {
        const res = await apiFetch("/api/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            messages: currentMessages,
            conversation_id: conversationId,
            project_id: projectId,
            mode,
            model_name: modelName,
          }),
          signal: abortController.signal,
        })

        if (!res.ok || !res.body) {
          throw new Error(`HTTP ${res.status}`)
        }

        await consumeNdjsonStream(res.body, (event) => {
          setState((prev) => applyEvent(prev, event, onConversationCreated))
        })
      } catch (err) {
        if ((err as Error).name === "AbortError") {
          setState((prev) => ({ ...prev, status: "ready" }))
        } else {
          setState((prev) => ({
            ...prev,
            status: "error",
            error: err instanceof Error ? err.message : "发送失败",
          }))
        }
      } finally {
        abortRef.current = null
      }
    },
    [conversationId, projectId, mode, modelName, state.messages, state.status, appendUserMessage, onConversationCreated],
  )

  const reload = useCallback(() => {
    const lastUser = [...state.messages].reverse().find((m) => m.role === "user")
    if (!lastUser) return
    const text = lastUser.parts.find((p): p is TextPart => p.type === "text")?.text ?? ""
    const idx = state.messages.indexOf(lastUser)
    setState((prev) => ({
      ...prev,
      messages: prev.messages.slice(0, idx + 1),
      status: "ready",
      error: null,
    }))
    void sendMessage(text)
  }, [state.messages, sendMessage])

  return {
    messages: state.messages,
    status: state.status,
    error: state.error,
    sendMessage,
    stop,
    reload,
  }
}

async function consumeNdjsonStream(
  stream: ReadableStream<Uint8Array>,
  onEvent: (event: Record<string, unknown>) => void,
) {
  const reader = stream.getReader()
  const decoder = new TextDecoder()
  let buffer = ""

  while (true) {
    const { value, done } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    let idx = buffer.indexOf("\n")
    while (idx >= 0) {
      const line = buffer.slice(0, idx).trim()
      buffer = buffer.slice(idx + 1)
      if (line) {
        try {
          onEvent(JSON.parse(line) as Record<string, unknown>)
        } catch {
          // ignore malformed lines
        }
      }
      idx = buffer.indexOf("\n")
    }
  }

  const lastLine = buffer.trim()
  if (lastLine) {
    try {
      onEvent(JSON.parse(lastLine) as Record<string, unknown>)
    } catch {
      // ignore
    }
  }
}

function applyEvent(
  state: ChatState,
  event: Record<string, unknown>,
  onConversationCreated?: (id: string) => void,
): ChatState {
  const type = event.type as string
  const messages = [...state.messages]

  switch (type) {
    case "user_message": {
      const msg = event.message as ChatMessage
      if (!messages.find((m) => m.id === msg.id)) {
        messages.push(msg)
      }
      return { ...state, messages }
    }

    case "conversation_start": {
      const id = event.conversation_id as string
      if (id) onConversationCreated?.(id)
      return state
    }

    case "assistant_start": {
      const msg = (event.message as ChatMessage) || { id: `assistant-${Date.now()}`, role: "assistant", parts: [] }
      messages.push(msg)
      return { ...state, status: "streaming" }
    }

    case "text_delta": {
      const lastAssistant = findLastAssistant(messages)
      if (lastAssistant) {
        const text = (event.text as string) || ""
        const textPart = lastAssistant.parts.find((p): p is TextPart => p.type === "text")
        if (textPart) {
          textPart.text += text
          textPart.state = "streaming"
        } else {
          lastAssistant.parts.push({ type: "text", text, state: "streaming" })
        }
      }
      return { ...state, messages, status: "streaming" }
    }

    case "reasoning_delta": {
      const lastAssistant = findLastAssistant(messages)
      if (lastAssistant) {
        const text = (event.text as string) || ""
        const reasoningPart = lastAssistant.parts.find((p): p is ReasoningPart => p.type === "reasoning")
        if (reasoningPart) {
          reasoningPart.text += text
          reasoningPart.state = "streaming"
        } else {
          lastAssistant.parts.push({ type: "reasoning", text, state: "streaming" })
        }
      }
      return { ...state, messages, status: "streaming" }
    }

    case "tool_call":
    case "tool_result": {
      const lastAssistant = findLastAssistant(messages)
      if (lastAssistant) {
        const toolCallId = event.tool_call_id as string
        const existingIdx = lastAssistant.parts.findIndex(
          (p): p is ToolInvocationPart => p.type === "tool-invocation" && p.toolCallId === toolCallId,
        )
        const newState = event.state as ToolInvocationPart["state"]
        if (existingIdx >= 0) {
          const existing = lastAssistant.parts[existingIdx] as ToolInvocationPart
          existing.state = newState
          if (event.input) existing.input = event.input as Record<string, unknown>
          if (event.output) existing.output = event.output as Record<string, unknown>
        } else {
          const part: ToolInvocationPart = {
            type: "tool-invocation",
            toolCallId,
            toolName: event.tool_name as string,
            state: newState,
            input: (event.input as Record<string, unknown>) || {},
            output: (event.output as Record<string, unknown>) || {},
          }
          lastAssistant.parts.push(part as MessagePart)
        }
      }
      return { ...state, messages, status: "streaming" }
    }

    case "artifact": {
      const lastAssistant = findLastAssistant(messages)
      if (lastAssistant) {
        lastAssistant.parts.push({
          type: "artifact",
          artifactType: event.artifact_type as string,
          name: event.name as string,
        })
      }
      return { ...state, messages, status: "streaming" }
    }

    case "approval_request": {
      const lastAssistant = findLastAssistant(messages)
      if (lastAssistant) {
        lastAssistant.parts.push({
          type: "approval-request",
          approvalId: event.approval_id as string,
          capability: event.capability as string,
          riskTier: event.risk_tier as string,
          runId: event.run_id as string,
          projectId: event.project_id as string,
        })
      }
      return { ...state, messages, status: "ready" }
    }

    case "assistant_done": {
      const msg = event.message as ChatMessage
      const idx = messages.findIndex((m) => m.id === msg.id)
      if (idx >= 0) {
        messages[idx] = msg
      } else {
        messages.push(msg)
      }
      return { ...state, messages, status: "ready" }
    }

    case "done":
      return { ...state, status: "ready" }

    case "error":
      return { ...state, status: "error", error: (event.message as string) || "流式响应出错" }

    default:
      return state
  }
}

function findLastAssistant(messages: ChatMessage[]): ChatMessage | undefined {
  for (let i = messages.length - 1; i >= 0; i--) {
    if (messages[i].role === "assistant") return messages[i]
  }
  return undefined
}
