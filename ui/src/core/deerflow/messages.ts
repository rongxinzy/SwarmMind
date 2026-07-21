import type { AIMessage, Message } from "@langchain/langgraph-sdk"

import { normalizeArtifactPath } from "./artifacts"

interface GenericMessageGroup<T = string> {
  type: T
  id: string | undefined
  messages: Message[]
}

type HumanMessageGroup = GenericMessageGroup<"human">

type AssistantProcessingGroup = GenericMessageGroup<"assistant:processing">

type AssistantMessageGroup = GenericMessageGroup<"assistant">

type AssistantPresentFilesGroup = GenericMessageGroup<"assistant:present-files">

type AssistantClarificationGroup = GenericMessageGroup<"assistant:clarification">

type AssistantSubagentGroup = GenericMessageGroup<"assistant:subagent">

export type MessageGroup =
  | HumanMessageGroup
  | AssistantProcessingGroup
  | AssistantMessageGroup
  | AssistantPresentFilesGroup
  | AssistantClarificationGroup
  | AssistantSubagentGroup

const HIDDEN_CONTROL_MESSAGE_NAMES = new Set([
  "summary",
  "loop_warning",
  "todo_reminder",
  "todo_completion_reminder",
])

const MARKDOWN_ARTIFACT_TARGET_RE = /!?\[[^\]]*]\(([^)\s]+)(?:\s+"[^"]*")?\)/g
const RAW_ARTIFACT_PATH_RE = /(?:^|[\s"'(])((?:\/?mnt\/user-data(?:\/[^\s)"'<>`]*)?))/g

export function getMessageGroups(messages: Message[]): MessageGroup[] {
  if (messages.length === 0) {
    return []
  }

  const groups: MessageGroup[] = []

  function lastOpenGroup() {
    const last = groups[groups.length - 1]
    if (
      last &&
      last.type !== "human" &&
      last.type !== "assistant" &&
      last.type !== "assistant:clarification"
    ) {
      return last
    }
    return null
  }

  for (const message of messages) {
    if (isHiddenFromUIMessage(message)) {
      continue
    }

    if (message.type === "human") {
      groups.push({ id: message.id, type: "human", messages: [message] })
      continue
    }

    if (message.type === "tool") {
      if (isClarificationToolMessage(message)) {
        lastOpenGroup()?.messages.push(message)
        groups.push({
          id: message.id,
          type: "assistant:clarification",
          messages: [message],
        })
      } else {
        const open = lastOpenGroup()
        if (open) {
          open.messages.push(message)
        } else {
          console.error("Unexpected tool message outside a processing group", message)
        }
      }
      continue
    }

    if (message.type === "ai") {
      if (hasPresentFiles(message)) {
        groups.push({
          id: message.id,
          type: "assistant:present-files",
          messages: [message],
        })
      } else if (hasSubagent(message)) {
        groups.push({
          id: message.id,
          type: "assistant:subagent",
          messages: [message],
        })
      } else if (hasReasoning(message) || hasToolCalls(message)) {
        const lastGroup = groups[groups.length - 1]
        if (lastGroup?.type !== "assistant:processing") {
          groups.push({
            id: message.id,
            type: "assistant:processing",
            messages: [message],
          })
        } else {
          lastGroup.messages.push(message)
        }
      }

      if (hasContent(message) && !hasToolCalls(message)) {
        groups.push({ id: message.id, type: "assistant", messages: [message] })
      }
    }
  }

  return groups
}

export function getAssistantTurnCopyData(
  messages: Message[],
  { isStreaming = false }: { isStreaming?: boolean } = {},
) {
  if (isStreaming) {
    return null
  }

  return (
    [...messages]
      .reverse()
      .filter((message) => message.type === "ai")
      .map((message) => {
        const content = extractContentFromMessage(message)
        return content.length > 0 ? content : (extractReasoningContentFromMessage(message) ?? "")
      })
      .find((content) => content.length > 0) ?? null
  )
}

export function extractTextFromMessage(message: Message) {
  if (typeof message.content === "string") {
    return splitInlineReasoningFromAIMessage(message)?.content ?? message.content.trim()
  }
  if (Array.isArray(message.content)) {
    return message.content
      .map((content) =>
        typeof content === "string" ? content : content.type === "text" ? content.text : "",
      )
      .join("\n")
      .trim()
  }
  return ""
}

const THINK_OPEN_TAG = "<think>"
const THINK_TAG_RE = /<think>\s*([\s\S]*?)\s*<\/think>/g

function splitInlineReasoning(content: string) {
  const reasoningParts: string[] = []

  let cleaned = content.replace(THINK_TAG_RE, (_, reasoning: string) => {
    const normalized = reasoning.trim()
    if (normalized) {
      reasoningParts.push(normalized)
    }
    return ""
  })

  const openTagIndex = cleaned.indexOf(THINK_OPEN_TAG)
  if (openTagIndex !== -1 && cleaned[openTagIndex - 1] !== "`") {
    const tail = cleaned.slice(openTagIndex + THINK_OPEN_TAG.length).trim()
    if (tail) {
      reasoningParts.push(tail)
    }
    cleaned = cleaned.slice(0, openTagIndex)
  }

  return {
    content: cleaned.trim(),
    reasoning: reasoningParts.length > 0 ? reasoningParts.join("\n\n") : null,
  }
}

function splitInlineReasoningFromAIMessage(message: Message) {
  if (message.type !== "ai" || typeof message.content !== "string") {
    return null
  }
  return splitInlineReasoning(message.content)
}

export function extractContentFromMessage(message: Message) {
  if (typeof message.content === "string") {
    return splitInlineReasoningFromAIMessage(message)?.content ?? message.content.trim()
  }
  if (Array.isArray(message.content)) {
    return message.content
      .map((content) => {
        if (typeof content === "string") {
          return content
        }
        switch (content.type) {
          case "text":
            return content.text
          case "image_url":
            return `![image](${extractURLFromImageURLContent(content.image_url)})`
          default:
            return ""
        }
      })
      .join("\n")
      .trim()
  }
  return ""
}

export function extractReasoningContentFromMessage(message: Message) {
  if (message.type !== "ai") {
    return null
  }
  if (
    message.additional_kwargs &&
    "reasoning_content" in message.additional_kwargs
  ) {
    return message.additional_kwargs.reasoning_content as string | null
  }
  if (Array.isArray(message.content)) {
    const part = message.content[0]
    if (part && typeof part === "object" && "thinking" in part) {
      return part.thinking as string
    }
  }
  if (typeof message.content === "string") {
    return splitInlineReasoning(message.content).reasoning
  }
  return null
}

export function extractURLFromImageURLContent(
  content:
    | string
    | {
        url: string
      },
) {
  if (typeof content === "string") {
    return content
  }
  return content.url
}

export function hasContent(message: Message) {
  if (typeof message.content === "string") {
    return (splitInlineReasoningFromAIMessage(message)?.content ?? message.content.trim()).length > 0
  }
  if (Array.isArray(message.content)) {
    return message.content.length > 0
  }
  return false
}

export function hasReasoning(message: Message) {
  if (message.type !== "ai") {
    return false
  }
  if (typeof message.additional_kwargs?.reasoning_content === "string") {
    return true
  }
  if (Array.isArray(message.content)) {
    const part = message.content[0]
    return (part as unknown as { type: "thinking" })?.type === "thinking"
  }
  if (typeof message.content === "string") {
    return splitInlineReasoning(message.content).reasoning !== null
  }
  return false
}

export function hasToolCalls(message: Message) {
  return message.type === "ai" && message.tool_calls && message.tool_calls.length > 0
}

export function hasPresentFiles(message: Message) {
  return (
    message.type === "ai" &&
    message.tool_calls?.some((toolCall) => toolCall.name === "present_files")
  )
}

export function isClarificationToolMessage(message: Message) {
  return message.type === "tool" && message.name === "ask_clarification"
}

export function extractPresentFilesFromMessage(message: Message) {
  if (message.type !== "ai" || !hasPresentFiles(message)) {
    return []
  }
  const files: string[] = []
  for (const toolCall of message.tool_calls ?? []) {
    if (
      toolCall.name === "present_files" &&
      Array.isArray(toolCall.args.filepaths)
    ) {
      files.push(...(toolCall.args.filepaths as string[]))
    }
  }
  return files
}

export function extractArtifactPathsFromMessage(message: Message) {
  const files = new Set<string>(extractPresentFilesFromMessage(message))
  for (const path of extractArtifactPathsFromText(extractContentFromMessage(message))) {
    files.add(path)
  }
  for (const file of extractFilesFromMessage(message)) {
    const path = normalizeArtifactPath(file.path)
    if (path) {
      files.add(path)
    }
  }

  if (message.type !== "ai") {
    return [...files]
  }

  for (const toolCall of message.tool_calls ?? []) {
    if (toolCall.name !== "write_file" && toolCall.name !== "str_replace") {
      continue
    }
    const args = (toolCall.args ?? {}) as Record<string, unknown>
    const path = typeof args.path === "string" ? normalizeArtifactPath(args.path) : null
    if (path) {
      files.add(path)
    }
  }

  return [...files]
}

export function extractArtifactPathsFromText(content: string) {
  const files = new Set<string>()

  let markdownMatch: RegExpExecArray | null
  while ((markdownMatch = MARKDOWN_ARTIFACT_TARGET_RE.exec(content)) !== null) {
    const path = normalizeArtifactPath(decodeArtifactReference(markdownMatch[1]))
    if (path) {
      files.add(path)
    }
  }

  let rawMatch: RegExpExecArray | null
  while ((rawMatch = RAW_ARTIFACT_PATH_RE.exec(content)) !== null) {
    const path = normalizeArtifactPath(decodeArtifactReference(rawMatch[1]))
    if (path) {
      files.add(path)
    }
  }

  return [...files]
}

function decodeArtifactReference(path: string | undefined) {
  if (!path) {
    return undefined
  }
  try {
    return decodeURIComponent(path)
  } catch {
    return path
  }
}

export function hasSubagent(message: AIMessage) {
  for (const toolCall of message.tool_calls ?? []) {
    if (toolCall.name === "task") {
      return true
    }
  }
  return false
}

export function findToolCallResult(toolCallId: string, messages: Message[]) {
  for (const message of messages) {
    if (message.type === "tool" && message.tool_call_id === toolCallId) {
      const content = extractTextFromMessage(message)
      if (content) {
        return content
      }
    }
  }
  return undefined
}

export function isHiddenFromUIMessage(message: Message) {
  if (message.additional_kwargs?.hide_from_ui === true) {
    return true
  }
  return typeof message.name === "string" && HIDDEN_CONTROL_MESSAGE_NAMES.has(message.name)
}

/**
 * Represents a file stored in message additional_kwargs.files.
 * Kept aligned with DeerFlow's native message metadata shape.
 */
export interface FileInMessage {
  filename: string
  size: number
  path?: string
  status?: "uploading" | "uploaded"
}

export function stripUploadedFilesTag(content: string) {
  return content.replace(/<uploaded_files>[\s\S]*?<\/uploaded_files>/g, "").trim()
}

export function parseUploadedFiles(content: string): FileInMessage[] {
  const uploadedFilesRegex = /<uploaded_files>([\s\S]*?)<\/uploaded_files>/
  const match = uploadedFilesRegex.exec(content)

  if (!match) {
    return []
  }

  const uploadedFilesContent = match[1]
  if (
    uploadedFilesContent?.includes("No files have been uploaded yet.") ||
    uploadedFilesContent?.includes("(empty)")
  ) {
    return []
  }

  const fileRegex = /- ([^\n(]+)\s*\(([^)]+)\)\s*\n\s*Path:\s*([^\n]+)/g
  const files: FileInMessage[] = []
  let fileMatch: RegExpExecArray | null

  while ((fileMatch = fileRegex.exec(uploadedFilesContent ?? "")) !== null) {
    files.push({
      filename: fileMatch[1].trim(),
      size: Number.parseInt(fileMatch[2].trim(), 10) || 0,
      path: fileMatch[3].trim(),
    })
  }

  return files
}

export function extractFilesFromMessage(message: Message): FileInMessage[] {
  const files = message.additional_kwargs?.files
  if (Array.isArray(files) && files.length > 0) {
    return files.filter(isFileInMessage)
  }

  const rawContent = extractContentFromMessage(message)
  return rawContent.includes("<uploaded_files>") ? parseUploadedFiles(rawContent) : []
}

function isFileInMessage(file: unknown): file is FileInMessage {
  if (!file || typeof file !== "object") {
    return false
  }
  const candidate = file as Partial<FileInMessage>
  return typeof candidate.filename === "string" && typeof candidate.size === "number"
}
