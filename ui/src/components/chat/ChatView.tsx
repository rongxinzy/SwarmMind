import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import {
  Conversation,
  ConversationContent,
  ConversationScrollButton,
} from "@/components/ai-elements/conversation"
import {
  DeerFlowInputBox,
  type DeerFlowInputMode,
} from "@/components/deerflow/DeerFlowInputBox"
import { ArtifactWorkspacePanel } from "@/components/deerflow/ArtifactWorkspacePanel"
import { TokenUsageIndicator } from "@/components/deerflow/TokenUsageIndicator"
import { TodoList } from "@/components/deerflow/TodoList"
import { Spinner } from "@/components/ui/spinner"
import { useSwarmChat } from "@/hooks/useSwarmChat"
import { MessageRenderer } from "./MessageRenderer"
import { ChatEmptyState } from "./ChatEmptyState"
import { apiFetchJson } from "@/lib/api"
import { toast } from "sonner"
import {
  extractArtifactPathsFromMessage,
  extractContentFromMessage,
  stripUploadedFilesTag,
} from "@/core/deerflow/messages"
import {
  type ArtifactMetadata,
  type ArtifactMetadataIndex,
  buildArtifactMetadataIndex,
  findLatestWriteFileArtifactReference,
  isWriteFileArtifactReference,
  mergeArtifactPaths,
  parseWriteFileArtifactReference,
} from "@/core/deerflow/artifacts"
import type { DeerFlowPromptInputMessage } from "@/core/deerflow/input"
import { cn } from "@/lib/utils"
import type { ChatMessage } from "@/types/chat"

interface ChatViewProps {
  conversationId?: string
  onConversationCreated: (id: string, title: string) => void
  isLoadingConversations?: boolean
}

interface ArtifactListResponse {
  items: ArtifactMetadata[]
  total: number
}

export function ChatView({
  conversationId,
  onConversationCreated,
  isLoadingConversations,
}: ChatViewProps) {
  const handleConversationCreated = useCallback(
    (id: string, title?: string) => {
      onConversationCreated(id, title ?? "New Chat")
    },
    [onConversationCreated],
  )

  const [input, setInput] = useState("")
  const [mode, setMode] = useState<DeerFlowInputMode>("flash")
  const [modelName, setModelName] = useState<string | undefined>(undefined)
  const { messages, artifacts, planSteps, status, error, sendMessage, stop, reload } = useSwarmChat({
    conversationId,
    mode,
    modelName,
    onConversationCreated: handleConversationCreated,
  })
  const [selectedArtifact, setSelectedArtifact] = useState<string | null>(null)
  const [artifactPanelOpen, setArtifactPanelOpen] = useState(false)
  const [artifactMetadataByPath, setArtifactMetadataByPath] = useState<ArtifactMetadataIndex>({})
  const [followups, setFollowups] = useState<string[]>([])
  const [followupsLoading, setFollowupsLoading] = useState(false)
  const wasGeneratingRef = useRef(false)
  const lastFollowupSourceRef = useRef<string | null>(null)
  const autoArtifactPreviewSuppressedRef = useRef(false)

  useEffect(() => {
    if (error) {
      toast.error(error)
    }
  }, [error])

  const handleSubmit = useCallback(
    async (message: DeerFlowPromptInputMessage) => {
      if (!message.text.trim()) return
      setFollowups([])
      setFollowupsLoading(false)
      autoArtifactPreviewSuppressedRef.current = false
      await sendMessage(message.text, message.files)
      setInput("")
    },
    [sendMessage],
  )

  const isStreaming = status === "streaming"
  const isSubmitted = status === "submitted"
  const isGenerating = isStreaming || isSubmitted
  const isEmpty = messages.length === 0 && !isLoadingConversations
  const artifactFiles = useMemo(() => {
    const inferred: string[][] = []
    for (const message of messages) {
      inferred.push(extractArtifactPathsFromMessage(message))
    }
    return mergeArtifactPaths(artifacts, ...inferred)
  }, [artifacts, messages])
  const artifactFilesKey = artifactFiles.join("\n")
  const panelArtifactFiles = useMemo(() => {
    if (!selectedArtifact || !isWriteFileArtifactReference(selectedArtifact)) {
      return artifactFiles
    }
    const writeFilePath = parseWriteFileArtifactReference(selectedArtifact)?.path
    return [
      selectedArtifact,
      ...artifactFiles.filter((file) => file !== writeFilePath),
    ]
  }, [artifactFiles, selectedArtifact])

  useEffect(() => {
    if (!conversationId) {
      setArtifactMetadataByPath({})
      return
    }
    if (isGenerating) {
      return
    }

    let cancelled = false
    apiFetchJson<ArtifactListResponse>(`/conversations/${conversationId}/artifacts`)
      .then((data) => {
        if (!cancelled) {
          setArtifactMetadataByPath(buildArtifactMetadataIndex(data.items))
        }
      })
      .catch(() => {
        if (!cancelled) {
          setArtifactMetadataByPath({})
        }
      })

    return () => {
      cancelled = true
    }
  }, [artifactFilesKey, conversationId, isGenerating])

  useEffect(() => {
    setFollowups([])
    setFollowupsLoading(false)
    lastFollowupSourceRef.current = null
    wasGeneratingRef.current = false
    autoArtifactPreviewSuppressedRef.current = false
  }, [conversationId])

  useEffect(() => {
    const wasGenerating = wasGeneratingRef.current
    wasGeneratingRef.current = isGenerating
    if (!conversationId || isGenerating || status !== "ready" || !wasGenerating) {
      return
    }

    const lastAssistant = [...messages]
      .reverse()
      .find((message) => message.type === "ai" && extractContentFromMessage(message).trim().length > 0)
    const sourceId = lastAssistant?.id ?? null
    if (!sourceId || lastFollowupSourceRef.current === sourceId) {
      return
    }
    lastFollowupSourceRef.current = sourceId

    const recent = messages
      .map(toSuggestionMessage)
      .filter((message): message is { role: "user" | "assistant"; content: string } => message !== null)
      .slice(-6)
    if (recent.length === 0) {
      return
    }

    let cancelled = false
    setFollowups([])
    setFollowupsLoading(true)
    apiFetchJson<{ suggestions: string[] }>(`/api/threads/${conversationId}/suggestions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        messages: recent,
        n: 3,
        model_name: modelName,
      }),
    })
      .then((data) => {
        if (!cancelled) {
          setFollowups((data.suggestions ?? []).filter(Boolean).slice(0, 3))
        }
      })
      .catch(() => {
        if (!cancelled) {
          setFollowups([])
        }
      })
      .finally(() => {
        if (!cancelled) {
          setFollowupsLoading(false)
        }
      })

    return () => {
      cancelled = true
    }
  }, [conversationId, isGenerating, messages, modelName, status])

  useEffect(() => {
    if (!selectedArtifact) {
      return
    }
    if (isWriteFileArtifactReference(selectedArtifact)) {
      return
    }
    if (!artifactFiles.includes(selectedArtifact)) {
      setSelectedArtifact(null)
      setArtifactPanelOpen(false)
    }
  }, [artifactFiles, selectedArtifact])

  useEffect(() => {
    if (!isGenerating || autoArtifactPreviewSuppressedRef.current) {
      return
    }
    const writeFileReference = findLatestWriteFileArtifactReference(messages)
    if (!writeFileReference) {
      return
    }
    setSelectedArtifact((current) => current === writeFileReference ? current : writeFileReference)
    setArtifactPanelOpen(true)
  }, [isGenerating, messages])

  const handleArtifactSelect = useCallback((file: string) => {
    autoArtifactPreviewSuppressedRef.current = false
    setSelectedArtifact(file)
    setArtifactPanelOpen(true)
  }, [])

  const handleFollowupSelect = useCallback(async (suggestion: string) => {
    if (isGenerating) {
      return
    }
    const current = input.trim()
    const nextMessage = current ? `${current}\n${suggestion}` : suggestion
    setInput(nextMessage)
    setFollowups([])
    setFollowupsLoading(false)
    autoArtifactPreviewSuppressedRef.current = false
    await sendMessage(nextMessage)
    setInput("")
  }, [input, isGenerating, sendMessage])

  const renderComposer = (placement: "empty" | "docked") => (
    <DeerFlowInputBox
      value={input}
      onValueChange={setInput}
      status={status}
      mode={mode}
      modelName={modelName}
      placement={placement}
      followups={placement === "docked" ? followups : []}
      followupsLoading={placement === "docked" ? followupsLoading : false}
      onModeChange={setMode}
      onModelChange={setModelName}
      onFollowupSelect={handleFollowupSelect}
      onFollowupsDismiss={() => {
        setFollowups([])
        setFollowupsLoading(false)
      }}
      onSubmit={handleSubmit}
      onStop={stop}
      autoFocus={placement === "empty"}
    />
  )

  return (
    <div className="relative flex flex-1 overflow-hidden bg-[#fbfbfa]">
      <div
        className={cn(
          "relative flex min-w-0 flex-1 flex-col overflow-hidden transition-[max-width] duration-300",
          artifactPanelOpen && selectedArtifact ? "lg:max-w-[calc(100%-520px)]" : "max-w-full",
        )}
      >
      {conversationId && (
        <div className="absolute right-4 top-4 z-10 flex items-center gap-2">
          <TokenUsageIndicator messages={messages} />
        </div>
      )}

      <Conversation className="flex-1">
        <ConversationContent
          className={
            isEmpty
              ? "mx-auto flex h-full w-full max-w-[920px] flex-col items-center justify-center px-4 pb-10 pt-16"
              : "mx-auto w-full max-w-[820px] px-4 py-8"
          }
        >
          {messages.length === 0 ? (
            isLoadingConversations ? (
              <div className="flex h-full items-center justify-center">
                <Spinner className="text-muted-foreground" />
              </div>
            ) : (
              <>
                <ChatEmptyState onSuggestion={setInput} />
                <div className="mt-3 w-full max-w-[720px]">
                  {renderComposer("empty")}
                </div>
              </>
            )
          ) : (
            <MessageRenderer
              conversationId={conversationId}
              messages={messages}
              artifactMetadataByPath={artifactMetadataByPath}
              isStreaming={isGenerating}
              onArtifactSelect={handleArtifactSelect}
              onReload={reload}
            />
          )}
        </ConversationContent>
        <ConversationScrollButton />
      </Conversation>

      {!isEmpty && (
        <div className="mx-auto w-full max-w-3xl px-4 pb-4">
          {planSteps.length > 0 && (
            <TodoList
              className="mb-2 shadow-sm"
              todos={planSteps}
            />
          )}
          {renderComposer("docked")}
        </div>
      )}
      </div>

      {artifactPanelOpen && selectedArtifact && (
        <ArtifactWorkspacePanel
          className="absolute inset-y-0 right-0 z-20 w-full max-w-[520px] shadow-[0_0_45px_rgba(0,0,0,0.08)] lg:relative lg:z-0 lg:w-[520px] lg:shadow-none"
          conversationId={conversationId}
          files={panelArtifactFiles}
          artifactMetadataByPath={artifactMetadataByPath}
          messages={messages}
          selectedFile={selectedArtifact}
          onSelect={setSelectedArtifact}
          onClose={() => {
            autoArtifactPreviewSuppressedRef.current = true
            setArtifactPanelOpen(false)
          }}
        />
      )}
    </div>
  )
}

function toSuggestionMessage(message: ChatMessage) {
  if (message.type !== "human" && message.type !== "ai") {
    return null
  }
  const content = stripUploadedFilesTag(extractContentFromMessage(message)).trim()
  if (!content) {
    return null
  }
  return {
    role: message.type === "human" ? "user" : "assistant",
    content,
  } as const
}
