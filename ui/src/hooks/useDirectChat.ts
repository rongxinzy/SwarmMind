"use client"

import { useCallback, useEffect, useRef, useState } from "react"
import { createOpenAI } from "@ai-sdk/openai"
import { streamText } from "ai"
import { apiFetchJson } from "@/lib/api"

export interface DirectChatMessage {
  id: string
  role: "user" | "assistant"
  content: string
  created_at?: string
}

export interface ChatModelInfo {
  id: string
  name: string
  provider: string
  model: string
  display_name: string
  description?: string | null
  supports_vision: boolean
  supports_thinking: boolean
  base_url: string
  api_key: string
  is_default: boolean
}

export type DirectChatStatus = "ready" | "streaming" | "error"

interface DirectChatState {
  messages: DirectChatMessage[]
  status: DirectChatStatus
  error: string | null
  models: ChatModelInfo[]
  selectedModelId: string | null
  isLoadingModels: boolean
}

interface ChatModelsResponse {
  models: ChatModelInfo[]
  default_model: string | null
}

interface ConversationResponse {
  id: string
  session_type: string
  title: string
  updated_at: string
}

interface MessageListResponse {
  items: { id: string; role: string; content: string; created_at: string }[]
  total: number
}

interface UseDirectChatOptions {
  conversationId?: string
  onConversationCreated?: (id: string, title: string) => void
}

export function useDirectChat({ conversationId, onConversationCreated }: UseDirectChatOptions) {
  const [state, setState] = useState<DirectChatState>({
    messages: [],
    status: "ready",
    error: null,
    models: [],
    selectedModelId: null,
    isLoadingModels: true,
  })
  const conversationIdRef = useRef<string | undefined>(conversationId)
  const notifiedIdsRef = useRef<Set<string>>(new Set())
  const abortRef = useRef<AbortController | null>(null)

  useEffect(() => {
    let cancelled = false
    async function loadModels() {
      try {
        const data = await apiFetchJson<ChatModelsResponse>("/chat/models")
        if (cancelled) return
        setState((prev) => ({
          ...prev,
          models: data.models,
          selectedModelId: prev.selectedModelId ?? data.default_model ?? (data.models[0]?.id || null),
          isLoadingModels: false,
        }))
      } catch (err) {
        if (cancelled) return
        setState((prev) => ({
          ...prev,
          error: err instanceof Error ? err.message : "加载模型列表失败",
          isLoadingModels: false,
        }))
      }
    }
    void loadModels()
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    conversationIdRef.current = conversationId
    if (!conversationId) {
      setState((prev) => ({ ...prev, messages: [], status: "ready", error: null }))
      return
    }

    let cancelled = false
    async function loadHistory() {
      try {
        const data = await apiFetchJson<MessageListResponse>(`/chat/conversations/${conversationId}/messages`)
        if (cancelled) return
        setState((prev) => ({
          ...prev,
          messages: data.items.map((m) => ({
            id: m.id,
            role: m.role as "user" | "assistant",
            content: m.content,
            created_at: m.created_at,
          })),
          status: "ready",
          error: null,
        }))
      } catch (err) {
        if (cancelled) return
        setState((prev) => ({
          ...prev,
          error: err instanceof Error ? err.message : "加载历史消息失败",
          status: "ready",
        }))
      }
    }
    void loadHistory()
    return () => {
      cancelled = true
    }
  }, [conversationId])

  const selectModel = useCallback((modelId: string) => {
    setState((prev) => ({ ...prev, selectedModelId: modelId }))
  }, [])

  const persistMessages = useCallback(
    async (conversationId: string, messages: { role: "user" | "assistant"; content: string }[]) => {
      return apiFetchJson<{ messages: DirectChatMessage[] }>(
        `/chat/conversations/${conversationId}/messages`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ messages }),
        },
      )
    },
    [],
  )

  const createConversation = useCallback(async () => {
    const data = await apiFetchJson<ConversationResponse>("/chat/conversations", { method: "POST" })
    conversationIdRef.current = data.id
    return data
  }, [])

  const sendMessage = useCallback(
    async (text: string) => {
      const trimmed = text.trim()
      if (!trimmed) return
      if (state.status === "streaming") return

      const currentModel = state.models.find((m) => m.id === state.selectedModelId) ?? state.models[0]
      if (!currentModel) {
        setState((prev) => ({ ...prev, error: "没有可用的模型", status: "error" }))
        return
      }

      setState((prev) => ({
        ...prev,
        status: "streaming",
        error: null,
        messages: [...prev.messages, { id: `local-user-${Date.now()}`, role: "user", content: trimmed }],
      }))

      abortRef.current?.abort()
      const abortController = new AbortController()
      abortRef.current = abortController

      try {
        let effectiveConversationId = conversationIdRef.current
        let isNewConversation = false
        if (!effectiveConversationId) {
          const created = await createConversation()
          effectiveConversationId = created.id
          isNewConversation = true
        }

        await persistMessages(effectiveConversationId, [{ role: "user", content: trimmed }])

        const openai = createOpenAI({
          baseURL: currentModel.base_url,
          apiKey: currentModel.api_key,
        })

        const previousMessages = state.messages.map((m) => ({
          role: m.role,
          content: m.content,
        }))

        const { textStream } = streamText({
          model: openai(currentModel.model),
          messages: [
            ...previousMessages,
            { role: "user" as const, content: trimmed },
          ],
          abortSignal: abortController.signal,
        })

        let assistantContent = ""
        for await (const chunk of textStream) {
          assistantContent += chunk
          setState((prev) => {
            const existing = prev.messages.find((m) => m.id === "assistant-streaming")
            if (existing) {
              return {
                ...prev,
                messages: prev.messages.map((m) =>
                  m.id === "assistant-streaming" ? { ...m, content: assistantContent } : m,
                ),
              }
            }
            return {
              ...prev,
              messages: [...prev.messages, { id: "assistant-streaming", role: "assistant", content: assistantContent }],
            }
          })
        }

        await persistMessages(effectiveConversationId, [
          { role: "assistant", content: assistantContent || " " },
        ])

        setState((prev) => ({
          ...prev,
          status: "ready",
          messages: prev.messages.map((m) =>
            m.id === "assistant-streaming" ? { ...m, id: `assistant-${Date.now()}` } : m,
          ),
        }))

        if (isNewConversation && effectiveConversationId && !notifiedIdsRef.current.has(effectiveConversationId)) {
          notifiedIdsRef.current.add(effectiveConversationId)
          onConversationCreated?.(effectiveConversationId, trimmed.slice(0, 50))
        }
      } catch (err) {
        const isAbort = (err as Error).name === "AbortError"
        setState((prev) => ({
          ...prev,
          status: isAbort ? "ready" : "error",
          error: isAbort ? null : err instanceof Error ? err.message : "发送失败",
          messages: prev.messages.filter((m) => m.id !== "assistant-streaming"),
        }))
      } finally {
        abortRef.current = null
      }
    },
    [state.status, state.messages, state.models, state.selectedModelId, createConversation, persistMessages, onConversationCreated],
  )

  const stop = useCallback(() => {
    abortRef.current?.abort()
    setState((prev) => ({ ...prev, status: "ready" }))
  }, [])

  return {
    messages: state.messages,
    status: state.status,
    error: state.error,
    models: state.models,
    selectedModelId: state.selectedModelId,
    isLoadingModels: state.isLoadingModels,
    selectModel,
    sendMessage,
    stop,
  }
}
