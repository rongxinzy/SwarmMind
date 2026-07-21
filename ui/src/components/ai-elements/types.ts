export type ChatStatus = "ready" | "submitted" | "streaming" | "error"

export type LanguageModelUsage = {
  inputTokens?: number
  outputTokens?: number
  totalTokens?: number
  reasoningTokens?: number
  cachedInputTokens?: number
}

export type FileUIPart = {
  type: "file"
  filename?: string
  mediaType?: string
  url?: string
  file?: File
}

export type SourceDocumentUIPart = {
  type: "source-document"
  title?: string
  filename?: string
  mediaType?: string
  url?: string
}

export type UIMessageRole = "system" | "user" | "assistant" | "data"

export type UIMessagePart =
  | {
      type: "text"
      text: string
    }
  | {
      type: string
      [key: string]: unknown
    }

export type UIMessage = {
  id?: string
  role: UIMessageRole
  parts: UIMessagePart[]
}

export type GeneratedImage = {
  base64: string
  mediaType: string
  uint8Array?: Uint8Array
}

export type SpeechResult = {
  audio: {
    base64: string
    mediaType: string
    uint8Array?: Uint8Array
  }
}

export type TranscriptionSegment = {
  text: string
  startSecond: number
  endSecond: number
}

export type TranscriptionResult = {
  segments: TranscriptionSegment[]
}

export type ToolState =
  | "input-streaming"
  | "input-available"
  | "output-available"
  | "output-denied"
  | "output-error"

export type ToolUIPart = {
  type: `tool-${string}`
  state: ToolState
  input?: unknown
  output?: unknown
  errorText?: string
}

export type DynamicToolUIPart = {
  type: "dynamic-tool"
  state: ToolState
  toolName: string
  input?: unknown
  output?: unknown
  errorText?: string
}

export type Tool = {
  description?: string
  inputSchema?: unknown
  jsonSchema?: unknown
}
