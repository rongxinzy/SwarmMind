import type { Message as DeerFlowMessage } from "@langchain/langgraph-sdk"
import { CopyIcon, FileIcon, Loader2Icon, RefreshCcwIcon } from "lucide-react"

import {
  Message,
  MessageAction,
  MessageActions,
  MessageContent,
} from "@/components/ai-elements/message"
import { ArtifactFileList } from "@/components/deerflow/ArtifactFileList"
import {
  fileExtension,
  fileName,
} from "@/components/deerflow/ArtifactFileList"
import { MarkdownContent } from "@/components/deerflow/MarkdownContent"
import { ProcessingGroup } from "@/components/deerflow/ProcessingGroup"
import { StreamingIndicator } from "@/components/deerflow/StreamingIndicator"
import { SubtaskGroup } from "@/components/deerflow/SubtaskGroup"
import { Badge } from "@/components/ui/badge"
import {
  type ArtifactMetadataIndex,
  artifactMetadataForPath,
  normalizeArtifactPath,
  resolveArtifactReference,
} from "@/core/deerflow/artifacts"
import {
  extractContentFromMessage,
  extractFilesFromMessage,
  extractPresentFilesFromMessage,
  extractReasoningContentFromMessage,
  extractTextFromMessage,
  getAssistantTurnCopyData,
  getMessageGroups,
  hasContent,
  stripUploadedFilesTag,
  type FileInMessage,
  type MessageGroup,
} from "@/core/deerflow/messages"
import { cn } from "@/lib/utils"
import type { ChatMessage } from "@/types/chat"

interface MessageRendererProps {
  conversationId?: string
  messages: ChatMessage[]
  artifactMetadataByPath?: ArtifactMetadataIndex
  isStreaming: boolean
  onArtifactSelect?: (file: string) => void
  onReload?: () => void
}

export function MessageRenderer({
  conversationId,
  messages,
  artifactMetadataByPath,
  isStreaming,
  onArtifactSelect,
  onReload,
}: MessageRendererProps) {
  const groups = getMessageGroups(messages)
  const lastGroupIndex = groups.length - 1

  return (
    <>
      {groups.map((group, index) => {
        const isLast = index === lastGroupIndex
        const from = group.type === "human" ? "user" : "assistant"
        const copyText = getAssistantTurnCopyData(group.messages, { isStreaming: isLast && isStreaming })

        return (
          <Message key={`${group.type}-${group.id ?? index}`} from={from} className="group/conversation-message relative w-full">
            <MessageContent className={cn(from === "assistant" && "w-full", from === "user" && "w-fit")}>
              <DeerFlowGroupRenderer
                conversationId={conversationId}
                artifactMetadataByPath={artifactMetadataByPath}
                group={group}
                isStreaming={isLast && isStreaming}
                onArtifactSelect={onArtifactSelect}
              />
            </MessageContent>
            {from === "assistant" && isLast && !isStreaming && (copyText !== null || onReload !== undefined) && (
              <MessageActions className="absolute -bottom-8 left-0 right-0 z-20 opacity-0 transition-opacity delay-200 duration-300 group-hover/conversation-message:opacity-100">
                {copyText && (
                  <MessageAction
                    label="复制"
                    onClick={() => {
                      void navigator.clipboard.writeText(copyText)
                    }}
                  >
                    <CopyIcon className="size-3" />
                  </MessageAction>
                )}
                {onReload && (
                  <MessageAction label="重试" onClick={onReload}>
                    <RefreshCcwIcon className="size-3" />
                  </MessageAction>
                )}
              </MessageActions>
            )}
          </Message>
        )
      })}
      {isStreaming && (
        <div className="flex w-full px-1 py-3">
          <StreamingIndicator className="text-muted-foreground" size="sm" />
        </div>
      )}
    </>
  )
}

interface DeerFlowGroupRendererProps {
  conversationId?: string
  artifactMetadataByPath?: ArtifactMetadataIndex
  group: MessageGroup
  isStreaming: boolean
  onArtifactSelect?: (file: string) => void
}

function DeerFlowGroupRenderer({
  conversationId,
  artifactMetadataByPath,
  group,
  isStreaming,
  onArtifactSelect,
}: DeerFlowGroupRendererProps) {
  if (group.type === "human" || group.type === "assistant") {
    return (
      <>
        {group.messages.map((message) => (
          <MessageListItem
            key={message.id ?? `${group.id}-${extractTextFromMessage(message)}`}
            conversationId={conversationId}
            message={message}
            artifactMetadataByPath={artifactMetadataByPath}
            isStreaming={isStreaming}
            onArtifactSelect={onArtifactSelect}
          />
        ))}
      </>
    )
  }

  if (group.type === "assistant:clarification") {
    const message = group.messages[0]
    return message && hasContent(message) ? (
      <MarkdownContent
        conversationId={conversationId}
        content={extractContentFromMessage(message)}
        isLoading={isStreaming}
        onArtifactSelect={onArtifactSelect}
      />
    ) : null
  }

  if (group.type === "assistant:present-files") {
    const files = group.messages.flatMap(extractPresentFilesFromMessage)
    const message = group.messages[0]
    return (
      <div className="w-full space-y-4">
        {message && hasContent(message) && (
          <MarkdownContent
            conversationId={conversationId}
            content={extractContentFromMessage(message)}
            isLoading={isStreaming}
            onArtifactSelect={onArtifactSelect}
          />
        )}
        <ArtifactFileList
          conversationId={conversationId}
          files={files}
          artifactMetadataByPath={artifactMetadataByPath}
          onSelect={onArtifactSelect}
        />
      </div>
    )
  }

  if (group.type === "assistant:subagent") {
    return (
      <SubtaskGroup
        conversationId={conversationId}
        messages={group.messages}
        isLoading={isStreaming}
        onArtifactSelect={onArtifactSelect}
      />
    )
  }

  return (
    <ProcessingGroup
      conversationId={conversationId}
      messages={group.messages}
      isLoading={isStreaming}
      onArtifactSelect={onArtifactSelect}
    />
  )
}

function MessageListItem({
  conversationId,
  message,
  artifactMetadataByPath,
  isStreaming,
  onArtifactSelect,
}: {
  conversationId?: string
  message: DeerFlowMessage
  artifactMetadataByPath?: ArtifactMetadataIndex
  isStreaming: boolean
  onArtifactSelect?: (file: string) => void
}) {
  const isHuman = message.type === "human"
  const rawContent = extractContentFromMessage(message)
  const reasoningContent = extractReasoningContentFromMessage(message)
  const files = isHuman ? extractFilesFromMessage(message) : []
  const contentToDisplay = isHuman ? stripUploadedFilesTag(rawContent) : rawContent

  if (!isHuman && reasoningContent && !rawContent) {
    return (
      <ProcessingGroup
        conversationId={conversationId}
        messages={[message]}
        isLoading={isStreaming}
        onArtifactSelect={onArtifactSelect}
      />
    )
  }

  if (!contentToDisplay) {
    return null
  }

  return (
    <div className={cn("flex flex-col gap-2", isHuman && "ml-auto items-end")}>
      {files.length > 0 && (
        <RichFilesList
          conversationId={conversationId}
          artifactMetadataByPath={artifactMetadataByPath}
          files={files}
          onArtifactSelect={onArtifactSelect}
        />
      )}
      {contentToDisplay && (
        <MarkdownContent
          className={cn(isHuman ? "text-sm" : "my-3")}
          conversationId={conversationId}
          content={contentToDisplay}
          isLoading={isStreaming}
          onArtifactSelect={onArtifactSelect}
        />
      )}
    </div>
  )
}

function RichFilesList({
  conversationId,
  artifactMetadataByPath,
  files,
  onArtifactSelect,
}: {
  conversationId?: string
  artifactMetadataByPath?: ArtifactMetadataIndex
  files: FileInMessage[]
  onArtifactSelect?: (file: string) => void
}) {
  return (
    <div className="mb-1 flex max-w-[min(28rem,100%)] flex-wrap justify-end gap-2">
      {files.map((file, index) => (
        <RichFileCard
          key={`${file.filename}-${file.path ?? index}`}
          conversationId={conversationId}
          artifactMetadataByPath={artifactMetadataByPath}
          file={file}
          onArtifactSelect={onArtifactSelect}
        />
      ))}
    </div>
  )
}

function RichFileCard({
  conversationId,
  artifactMetadataByPath,
  file,
  onArtifactSelect,
}: {
  conversationId?: string
  artifactMetadataByPath?: ArtifactMetadataIndex
  file: FileInMessage
  onArtifactSelect?: (file: string) => void
}) {
  const uploading = file.status === "uploading"
  const path = file.path
  const href = path ? resolveArtifactReference(conversationId, path) : undefined
  const artifactPath = normalizeArtifactPath(path)
  const artifactMetadata = artifactMetadataForPath(artifactMetadataByPath, artifactPath ?? path)
  const image = isImageFile(file.filename)
  const label = fileName(file.filename)
  const displaySize = artifactMetadata?.size_bytes ?? file.size

  if (uploading) {
    return (
      <div className="flex min-w-32 max-w-52 items-center gap-2 rounded-lg border border-[#e8e8e8] bg-white px-3 py-2 text-left shadow-sm opacity-70">
        <Loader2Icon className="size-4 shrink-0 animate-spin text-muted-foreground" />
        <FileSummary filename={file.filename} size={displaySize} status="上传中" />
      </div>
    )
  }

  if (image && href) {
    return (
      <a
        className="group relative block h-24 max-w-48 overflow-hidden rounded-lg border border-[#e8e8e8] bg-white shadow-sm"
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        onClick={(event) => {
          if (artifactPath && onArtifactSelect) {
            event.preventDefault()
            onArtifactSelect(artifactPath)
          }
        }}
      >
        <img
          className="h-full w-auto min-w-28 object-cover transition-transform duration-200 group-hover:scale-[1.03]"
          src={href}
          alt={label}
        />
      </a>
    )
  }

  const content = (
    <div className="flex min-w-32 max-w-52 items-center gap-2 rounded-lg border border-[#e8e8e8] bg-white px-3 py-2 text-left shadow-sm transition-colors hover:bg-[#fafafa]">
      <FileIcon className="size-4 shrink-0 text-muted-foreground" />
      <FileSummary filename={file.filename} size={displaySize} />
    </div>
  )

  return href ? (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      onClick={(event) => {
        if (artifactPath && onArtifactSelect) {
          event.preventDefault()
          onArtifactSelect(artifactPath)
        }
      }}
    >
      {content}
    </a>
  ) : (
    content
  )
}

function FileSummary({
  filename,
  size,
  status,
}: {
  filename: string
  size: number
  status?: string
}) {
  return (
    <span className="min-w-0 flex-1">
      <span className="block truncate text-xs font-medium leading-5 text-foreground" title={filename}>
        {fileName(filename)}
      </span>
      <span className="flex items-center gap-1.5 text-[10px] leading-4 text-muted-foreground">
        <Badge variant="secondary" className="h-4 rounded px-1.5 text-[10px] font-normal">
          {fileExtension(filename)}
        </Badge>
        <span>{status ?? formatBytes(size)}</span>
      </span>
    </span>
  )
}

const IMAGE_EXTENSIONS = new Set(["png", "jpg", "jpeg", "gif", "webp", "svg", "bmp"])

function isImageFile(filename: string) {
  return IMAGE_EXTENSIONS.has(filename.split(".").pop()?.toLowerCase() ?? "")
}

function formatBytes(bytes: number) {
  if (!bytes) {
    return "-"
  }
  const kb = bytes / 1024
  return kb < 1024 ? `${kb.toFixed(1)} KB` : `${(kb / 1024).toFixed(1)} MB`
}
