import type { Message } from "@langchain/langgraph-sdk"

const WRITE_FILE_ARTIFACT_PROTOCOL = "write-file:"
const ACTIVE_CONTENT_EXTENSIONS = new Set(["html", "svg", "xhtml"])

export interface WriteFileArtifactReference {
  path: string
  messageId: string | null
  toolCallId: string | null
}

export interface WriteFileArtifactState {
  content: string | null
  status: "complete" | "failed" | "writing"
}

export interface ArtifactMetadata {
  artifact_id: string
  conversation_id?: string | null
  project_id?: string | null
  message_id?: string | null
  run_id?: string | null
  task_id?: string | null
  author_role?: string | null
  name?: string | null
  path?: string | null
  storage_uri?: string | null
  mime_type?: string | null
  size_bytes?: number | null
  artifact_type?: string | null
  created_at?: string | null
}

export type ArtifactMetadataIndex = Record<string, ArtifactMetadata>

export function normalizeArtifactPath(path: string | undefined) {
  const decoded = decodeArtifactReference(path)
  const stripped = decoded?.trim().replace(/^\/+/, "").replace(/[.,;:]+$/, "")
  if (!stripped || (stripped !== "mnt/user-data" && !stripped.startsWith("mnt/user-data/"))) {
    return null
  }
  return `/${stripped}`
}

export function isVirtualArtifactPath(path: string | undefined) {
  return normalizeArtifactPath(path) !== null
}

export function isWriteFileArtifactReference(path: string | undefined): path is string {
  return typeof path === "string" && path.startsWith(WRITE_FILE_ARTIFACT_PROTOCOL)
}

export function createWriteFileArtifactReference({
  messageId,
  path,
  toolCallId,
}: {
  messageId?: string
  path: string
  toolCallId?: string
}) {
  const normalized = normalizeArtifactPath(path)
  if (!normalized) {
    return null
  }
  const url = new URL(`${WRITE_FILE_ARTIFACT_PROTOCOL}${normalized}`)
  if (messageId) {
    url.searchParams.set("message_id", messageId)
  }
  if (toolCallId) {
    url.searchParams.set("tool_call_id", toolCallId)
  }
  return url.toString()
}

export function parseWriteFileArtifactReference(reference: string | undefined): WriteFileArtifactReference | null {
  if (!isWriteFileArtifactReference(reference)) {
    return null
  }
  try {
    const url = new URL(reference)
    const path = normalizeArtifactPath(url.pathname)
    if (!path) {
      return null
    }
    return {
      path,
      messageId: url.searchParams.get("message_id"),
      toolCallId: url.searchParams.get("tool_call_id"),
    }
  } catch {
    return null
  }
}

export function artifactDisplayPath(path: string) {
  return parseWriteFileArtifactReference(path)?.path ?? path
}

export function artifactMetadataPath(artifact: ArtifactMetadata) {
  return normalizeArtifactPath(artifact.path ?? artifact.name ?? artifact.storage_uri ?? undefined)
}

export function buildArtifactMetadataIndex(artifacts: readonly ArtifactMetadata[] = []): ArtifactMetadataIndex {
  const index: ArtifactMetadataIndex = {}
  for (const artifact of artifacts) {
    const path = artifactMetadataPath(artifact)
    if (path) {
      index[path] = artifact
    }
  }
  return index
}

export function artifactMetadataForPath(index: ArtifactMetadataIndex | undefined, path: string | undefined) {
  if (!index || !path) {
    return undefined
  }
  const normalized = normalizeArtifactPath(artifactDisplayPath(path))
  return normalized ? index[normalized] : undefined
}

export function isActiveContentArtifactPath(path: string) {
  const displayPath = artifactDisplayPath(path)
  const name = displayPath.split("/").filter(Boolean).pop() ?? displayPath
  const ext = name.split(".").pop()?.toLowerCase()
  return ext !== undefined && ext !== name && ACTIVE_CONTENT_EXTENSIONS.has(ext)
}

export function isSkillArtifactPath(path: string | undefined) {
  const displayPath = path ? artifactDisplayPath(path) : ""
  return displayPath.toLowerCase().endsWith(".skill")
}

export function skillArtifactPreviewPath(path: string | undefined) {
  if (!path || !isSkillArtifactPath(path)) {
    return null
  }
  return `${artifactDisplayPath(path).replace(/\/+$/, "")}/SKILL.md`
}

export function mergeArtifactPaths(...sources: (Iterable<string | undefined> | undefined)[]) {
  const files = new Set<string>()
  for (const source of sources) {
    if (!source) {
      continue
    }
    for (const path of source) {
      const normalized = normalizeArtifactPath(path)
      if (normalized) {
        files.add(normalized)
      }
    }
  }
  return [...files]
}

export function artifactUrl(conversationId: string, path: string, download: boolean) {
  const normalized = normalizeArtifactPath(path)?.replace(/^\/+/, "") ?? path.replace(/^\/+/, "")
  const encodedPath = normalized.split("/").map(encodeURIComponent).join("/")
  return `/conversations/${encodeURIComponent(conversationId)}/artifacts/${encodedPath}${download ? "?download=true" : ""}`
}

export function resolveArtifactReference(conversationId: string | undefined, path: string) {
  const normalized = normalizeArtifactPath(path)
  if (!conversationId || !normalized) {
    return path
  }
  return artifactUrl(conversationId, normalized, false)
}

export function extractWriteFileArtifactContent(messages: readonly Message[], reference: string) {
  return getWriteFileArtifactState(messages, reference)?.content ?? null
}

export function getWriteFileArtifactState(
  messages: readonly Message[],
  reference: string,
): WriteFileArtifactState | null {
  const parsed = parseWriteFileArtifactReference(reference)
  if (!parsed?.messageId || !parsed.toolCallId) {
    return null
  }

  const selectedResult = findToolResult(messages, parsed.toolCallId)
  if (selectedResult !== undefined && !hasSuccessfulWriteResult(selectedResult)) {
    return { content: null, status: "failed" }
  }

  let content = ""
  let hasContent = false

  for (const message of messages) {
    if (message.type !== "ai") {
      continue
    }

    for (const toolCall of message.tool_calls ?? []) {
      const args = (toolCall.args ?? {}) as Record<string, unknown>
      if (
        toolCall.name !== "write_file" ||
        normalizeArtifactPath(typeof args.path === "string" ? args.path : undefined) !== parsed.path ||
        typeof args.content !== "string"
      ) {
        continue
      }

      const toolResult = findToolResult(messages, toolCall.id)
      const isSelected = toolCall.id === parsed.toolCallId && message.id === parsed.messageId
      const shouldInclude = hasSuccessfulWriteResult(toolResult) || (isSelected && toolResult === undefined)
      if (!shouldInclude) {
        continue
      }

      if (args.append === true && hasContent) {
        content += args.content
      } else {
        content = args.content
      }
      hasContent = true

      if (isSelected) {
        return {
          content,
          status: toolResult === undefined ? "writing" : "complete",
        }
      }
    }
  }

  return null
}

function findToolResult(messages: readonly Message[], toolCallId: string | undefined) {
  if (!toolCallId) {
    return undefined
  }

  for (const message of messages) {
    if (message.type === "tool" && message.tool_call_id === toolCallId) {
      return textContent(message.content)
    }
  }
  return undefined
}

function textContent(content: unknown) {
  if (typeof content === "string") {
    return content.trim()
  }
  if (!Array.isArray(content)) {
    return undefined
  }

  return content
    .map((part) => {
      if (typeof part === "object" && part !== null && "text" in part) {
        const text = (part as { text?: unknown }).text
        if (typeof text === "string") {
          return text
        }
      }
      return ""
    })
    .join("")
    .trim()
}

function hasSuccessfulWriteResult(toolResult: string | undefined) {
  return toolResult?.trim() === "OK"
}

export function findLatestWriteFileArtifactReference(messages: readonly Message[]) {
  for (let messageIndex = messages.length - 1; messageIndex >= 0; messageIndex -= 1) {
    const message = messages[messageIndex]
    if (message?.type === "human") {
      return null
    }
    if (message?.type !== "ai" || !message.tool_calls?.length) {
      continue
    }

    for (let toolCallIndex = message.tool_calls.length - 1; toolCallIndex >= 0; toolCallIndex -= 1) {
      const toolCall = message.tool_calls[toolCallIndex]
      if (!toolCall) {
        continue
      }
      if (toolCall.name !== "write_file") {
        return null
      }

      const args = (toolCall.args ?? {}) as Record<string, unknown>
      const path = typeof args.path === "string" ? args.path : undefined
      return path
        ? createWriteFileArtifactReference({
            messageId: message.id,
            path,
            toolCallId: toolCall.id,
          })
        : null
    }
  }

  return null
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
