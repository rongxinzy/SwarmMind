import { useCallback, useEffect, useRef, useState } from "react"
import {
  stripUploadedFilesTag,
  type FileInMessage,
} from "@/core/deerflow/messages"
import type { DeerFlowInputFilePart } from "@/core/deerflow/input"
import {
  derivePlanStepsFromMessages,
  normalizePlanSteps,
} from "@/core/deerflow/todos"
import { mergeArtifactPaths } from "@/core/deerflow/artifacts"
import { apiFetch, apiFetchJson } from "@/lib/api"
import type { ChatMessage, ChatPlanStep, ChatStatus } from "@/types/chat"

interface ChatState {
  messages: ChatMessage[]
  artifacts: string[]
  planSteps: ChatPlanStep[]
  status: ChatStatus
  error: string | null
}

interface UseSwarmChatOptions {
  conversationId?: string
  projectId?: string
  mode?: string
  modelName?: string
  onConversationCreated?: (id: string, title?: string) => void
}

interface ConversationSummary {
  id: string
}

interface UploadedFileInfo {
  filename: string
  size: number
  virtual_path: string
}

interface UploadResponse {
  files: UploadedFileInfo[]
}

export function useSwarmChat({
  conversationId,
  projectId,
  mode = "flash",
  modelName,
  onConversationCreated,
}: UseSwarmChatOptions) {
  const [state, setState] = useState<ChatState>({ messages: [], artifacts: [], planSteps: [], status: "ready", error: null })
  const abortRef = useRef<AbortController | null>(null)
  const notifiedConversationIdsRef = useRef(new Set<string>())

  const notifyConversationCreated = useCallback(
    (id: string, title?: string) => {
      const hasNotified = notifiedConversationIdsRef.current.has(id)
      if (hasNotified && title === undefined) {
        return
      }
      if (!hasNotified) {
        notifiedConversationIdsRef.current.add(id)
      }
      void Promise.resolve().then(() => onConversationCreated?.(id, title))
    },
    [onConversationCreated],
  )

  useEffect(() => {
    if (!conversationId) {
      setState((prev) => ({ ...prev, messages: [], artifacts: [], planSteps: [] }))
      return
    }

    let cancelled = false
    async function loadHistory() {
      try {
        const res = await apiFetch(`/api/chat/history?conversation_id=${conversationId}`)
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const data = (await res.json()) as { messages: ChatMessage[]; artifacts?: string[] }
        if (!cancelled) {
          setState({
            messages: data.messages,
            artifacts: mergeArtifactPaths(data.artifacts),
            planSteps: derivePlanStepsFromMessages(data.messages) ?? [],
            status: "ready",
            error: null,
          })
        }
      } catch (err) {
        if (!cancelled) {
          setState((prev) => ({ ...prev, error: err instanceof Error ? err.message : "加载历史失败" }))
        }
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

  const appendUserMessage = useCallback((text: string, files: FileInMessage[] = []) => {
    const userMessage: ChatMessage = {
      id: `local-human-${Date.now()}`,
      type: "human",
      content: text,
      additional_kwargs: files.length > 0 ? { files } : {},
      response_metadata: {},
    }
    setState((prev) => ({ ...prev, messages: [...prev.messages, userMessage] }))
    return userMessage
  }, [])

  const sendMessage = useCallback(
    async (text: string, fileParts?: DeerFlowInputFilePart[], replayMessages?: ChatMessage[]) => {
      const trimmedText = text.trim()
      if (!trimmedText) return
      if (state.status === "streaming" || state.status === "submitted") return

      abortRef.current?.abort()
      const abortController = new AbortController()
      abortRef.current = abortController

      const optimisticFiles = fileParts?.map(filePartToOptimisticFile) ?? []
      const localUserMessage = replayMessages ? null : appendUserMessage(trimmedText, optimisticFiles)
      let currentMessages = replayMessages ?? [...state.messages, localUserMessage as ChatMessage]
      let effectiveConversationId = conversationId

      setState((prev) => ({
        ...prev,
        messages: replayMessages ?? prev.messages,
        planSteps: [],
        status: "submitted",
        error: null,
      }))

      try {
        if (!replayMessages && fileParts && fileParts.length > 0) {
          if (!effectiveConversationId) {
            const created = await apiFetchJson<ConversationSummary>("/conversations", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ title: titleFromText(trimmedText) }),
            })
            effectiveConversationId = created.id
            notifyConversationCreated(created.id)
          }

          const files = await Promise.all(fileParts.map(filePartToFile))
          const uploadableFiles = files.filter((file): file is File => file !== null)
          if (uploadableFiles.length !== fileParts.length) {
            throw new Error("部分附件无法读取，请重新选择后再试")
          }

          const uploadResponse = await uploadFiles(effectiveConversationId, uploadableFiles)
          const uploadedFiles = uploadResponse.files.map(fileInfoToMessageFile)
          const contentWithFiles = appendUploadedFilesTag(trimmedText, uploadedFiles)

          if (localUserMessage?.id) {
            setState((prev) => ({
              ...prev,
              messages: prev.messages.map((message) =>
                message.id === localUserMessage.id
                  ? {
                      ...message,
                      content: contentWithFiles,
                      additional_kwargs: {
                        ...(message.additional_kwargs ?? {}),
                        files: uploadedFiles,
                      },
                    }
                  : message,
              ),
            }))
          }

          currentMessages = currentMessages.map((message) =>
            message.id === localUserMessage?.id
              ? {
                  ...message,
                  content: contentWithFiles,
                  additional_kwargs: {
                    ...(message.additional_kwargs ?? {}),
                    files: uploadedFiles,
                  },
                }
              : message,
          )
        }

        const res = await apiFetch("/api/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            messages: currentMessages,
            conversation_id: effectiveConversationId,
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
          const eventType = event.type as string
          const nextConversationId = eventType === "conversation_start" ? event.conversation_id : null
          if (typeof nextConversationId === "string" && nextConversationId) {
            notifyConversationCreated(nextConversationId)
          }
          if (eventType === "title") {
            const conversation = event.conversation
            if (conversation && typeof conversation === "object") {
              const nextId = (conversation as { id?: unknown }).id
              const nextTitle = (conversation as { title?: unknown }).title
              if (typeof nextId === "string" && nextId) {
                notifyConversationCreated(nextId, typeof nextTitle === "string" ? nextTitle : undefined)
              }
            }
          }
          setState((prev) => applyEvent(prev, event))
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
    [conversationId, projectId, mode, modelName, state.messages, state.status, appendUserMessage, notifyConversationCreated],
  )

  const reload = useCallback(() => {
    const lastUser = [...state.messages].reverse().find((message) => message.type === "human")
    if (!lastUser) return
    const text = messageText(lastUser)
    if (!text) return
    const idx = state.messages.indexOf(lastUser)
    const replayMessages = state.messages.slice(0, idx + 1)
    setState((prev) => ({
      ...prev,
      messages: replayMessages,
      status: "ready",
      error: null,
    }))
    void sendMessage(text, undefined, replayMessages)
  }, [state.messages, sendMessage])

  return {
    messages: state.messages,
    artifacts: state.artifacts,
    planSteps: state.planSteps,
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

  for (;;) {
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
          // Ignore malformed lines from interrupted streams.
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
      // Ignore.
    }
  }
}

function applyEvent(
  state: ChatState,
  event: Record<string, unknown>,
): ChatState {
  const type = event.type as string

  switch (type) {
    case "conversation_start": {
      return state
    }

    case "deerflow.message": {
      const message = normalizeMessage(event.message)
      if (!message) return state
      const nextMessages = upsertMessage(state.messages, message)
      const derivedPlanSteps = derivePlanStepsFromMessages(nextMessages)
      return {
        ...state,
        messages: nextMessages,
        planSteps: derivedPlanSteps ?? state.planSteps,
        status: message.type === "ai" || message.type === "tool" ? "streaming" : state.status,
      }
    }

    case "plan_steps": {
      return {
        ...state,
        planSteps: normalizePlanSteps(event.steps),
        status: state.status === "ready" ? "streaming" : state.status,
      }
    }

    case "artifacts": {
      const artifacts = Array.isArray(event.artifacts)
        ? event.artifacts.filter((path): path is string => typeof path === "string")
        : []
      return {
        ...state,
        artifacts: mergeArtifactPaths(state.artifacts, artifacts),
      }
    }

    case "done":
      return { ...state, status: "ready" }

    case "error":
      return { ...state, status: "error", error: (event.message as string) || "流式响应出错" }

    default:
      return state
  }
}

function normalizeMessage(value: unknown): ChatMessage | null {
  if (!value || typeof value !== "object") {
    return null
  }
  const message = value as ChatMessage
  if (!message.type) {
    return null
  }
  return {
    ...message,
    content: message.content ?? "",
    additional_kwargs: message.additional_kwargs ?? {},
    response_metadata: message.response_metadata ?? {},
  }
}

function upsertMessage(messages: ChatMessage[], incoming: ChatMessage) {
  const incomingIdentity = messageIdentity(incoming)
  const next = [...messages]

  if (incoming.type === "human") {
    const incomingText = comparableMessageText(incoming)
    const optimisticIndex = next.findIndex(
      (message) =>
        message.type === "human" &&
        typeof message.id === "string" &&
        message.id.startsWith("local-human-") &&
        comparableMessageText(message) === incomingText,
    )
    if (optimisticIndex >= 0) {
      next[optimisticIndex] = mergeMessage(next[optimisticIndex], incoming)
      return next
    }
  }

  if (incomingIdentity) {
    const existingIndex = next.findIndex((message) => messageIdentity(message) === incomingIdentity)
    if (existingIndex >= 0) {
      next[existingIndex] = mergeMessage(next[existingIndex], incoming)
      return next
    }
  }

  next.push(incoming)
  return next
}

function mergeMessage(existing: ChatMessage, incoming: ChatMessage): ChatMessage {
  const existingReasoning = existing.additional_kwargs?.reasoning_content
  const incomingReasoning = incoming.additional_kwargs?.reasoning_content
  return {
    ...existing,
    ...incoming,
    content: hasRenderableContent(incoming.content) ? incoming.content : existing.content,
    additional_kwargs: {
      ...(existing.additional_kwargs ?? {}),
      ...(incoming.additional_kwargs ?? {}),
      reasoning_content: incomingReasoning ?? existingReasoning,
    },
    response_metadata: {
      ...(existing.response_metadata ?? {}),
      ...(incoming.response_metadata ?? {}),
    },
  }
}

function messageIdentity(message: ChatMessage) {
  if (message.type === "tool" && "tool_call_id" in message && message.tool_call_id) {
    return `tool:${message.tool_call_id}`
  }
  if (message.id) {
    return `message:${message.id}`
  }
  const text = messageText(message)
  return text ? `${message.type}:${text}` : null
}

function messageText(message: ChatMessage) {
  const content = message.content
  if (typeof content === "string") {
    return content
  }
  if (Array.isArray(content)) {
    return content
      .map((part) => {
        if (typeof part === "string") return part
        if (part.type === "text") return part.text
        return ""
      })
      .join("\n")
  }
  return ""
}

function comparableMessageText(message: ChatMessage) {
  return stripUploadedFilesTag(messageText(message)).trim()
}

function hasRenderableContent(content: ChatMessage["content"]) {
  if (typeof content === "string") {
    return content.length > 0
  }
  return Array.isArray(content) && content.length > 0
}

function titleFromText(text: string) {
  return text.length > 50 ? `${text.slice(0, 50)}...` : text || "New Chat"
}

function filePartToOptimisticFile(filePart: DeerFlowInputFilePart): FileInMessage {
  const file = filePart.file
  return {
    filename: filePart.filename ?? file?.name ?? "file",
    size: file?.size ?? 0,
    status: "uploading",
  }
}

async function filePartToFile(filePart: DeerFlowInputFilePart): Promise<File | null> {
  if (filePart.file instanceof File) {
    const filename = filePart.filename ?? filePart.file.name
    const mediaType = filePart.mediaType ?? filePart.file.type
    if (filename === filePart.file.name && mediaType === filePart.file.type) {
      return filePart.file
    }
    return new File([filePart.file], filename, { type: mediaType })
  }

  if (!filePart.url || !filePart.filename) {
    return null
  }

  try {
    const response = await fetch(filePart.url)
    if (!response.ok) {
      return null
    }
    const blob = await response.blob()
    return new File([blob], filePart.filename, {
      type: filePart.mediaType ?? blob.type,
    })
  } catch {
    return null
  }
}

async function uploadFiles(threadId: string, files: File[]): Promise<UploadResponse> {
  const formData = new FormData()
  for (const file of files) {
    formData.append("files", file)
  }

  const response = await apiFetch(`/api/threads/${encodeURIComponent(threadId)}/uploads`, {
    method: "POST",
    body: formData,
  })
  if (!response.ok) {
    const detail = await response.text().catch(() => response.statusText)
    throw new Error(`附件上传失败: ${detail}`)
  }
  return response.json() as Promise<UploadResponse>
}

function fileInfoToMessageFile(fileInfo: UploadedFileInfo): FileInMessage {
  return {
    filename: fileInfo.filename,
    size: fileInfo.size,
    path: fileInfo.virtual_path,
    status: "uploaded",
  }
}

function appendUploadedFilesTag(text: string, files: FileInMessage[]) {
  if (files.length === 0) {
    return text
  }
  const fileLines = files
    .map((file) => `- ${file.filename} (${file.size})\n  Path: ${file.path ?? ""}`)
    .join("\n")
  return `${text}\n\n<uploaded_files>\n${fileLines}\n</uploaded_files>`
}
