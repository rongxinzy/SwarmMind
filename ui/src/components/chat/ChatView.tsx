import { useCallback, useEffect, useState } from "react"
import {
  Conversation,
  ConversationContent,
  ConversationScrollButton,
} from "@/components/ai-elements/conversation"
import {
  PromptInput,
  PromptInputBody,
  PromptInputFooter,
  PromptInputSubmit,
  PromptInputTextarea,
  PromptInputTools,
  type PromptInputMessage,
} from "@/components/ai-elements/prompt-input"
import { SquareIcon, TrendingUp } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Spinner } from "@/components/ui/spinner"
import { useSwarmChat } from "@/hooks/useSwarmChat"
import { MessageRenderer } from "./MessageRenderer"
import { ChatEmptyState } from "./ChatEmptyState"
import { apiFetchJson } from "@/lib/api"
import { toast } from "sonner"

interface ChatViewProps {
  conversationId?: string
  onConversationCreated: (id: string, title: string) => void
  onOpenProject: (id: string) => void
  onOpenApprovals?: () => void
  isLoadingConversations?: boolean
}

export function ChatView({
  conversationId,
  onConversationCreated,
  onOpenProject,
  onOpenApprovals,
  isLoadingConversations,
}: ChatViewProps) {
  const handleConversationCreated = useCallback(
    (id: string) => {
      onConversationCreated(id, "New Chat")
    },
    [onConversationCreated],
  )

  const { messages, status, error, sendMessage, stop, reload } = useSwarmChat({
    conversationId,
    onConversationCreated: handleConversationCreated,
  })
  const [input, setInput] = useState("")
  const [isPromoting, setIsPromoting] = useState(false)

  useEffect(() => {
    if (error) {
      toast.error(error)
    }
  }, [error])

  const handleSubmit = useCallback(
    async (message: PromptInputMessage) => {
      if (!message.text.trim()) return
      await sendMessage(message.text)
      setInput("")
    },
    [sendMessage],
  )

  const handlePromote = useCallback(async () => {
    if (!conversationId || isPromoting) return
    setIsPromoting(true)
    try {
      const data = (await apiFetchJson<{ project_id: string }>(`/conversations/${conversationId}/promote`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      })) as { project_id: string }
      toast.success("已升级为项目")
      onOpenProject(data.project_id)
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "升级失败")
    } finally {
      setIsPromoting(false)
    }
  }, [conversationId, isPromoting, onOpenProject])

  const isStreaming = status === "streaming"
  const isSubmitted = status === "submitted"

  return (
    <div className="relative flex flex-1 flex-col overflow-hidden">
      {conversationId && (
        <div className="absolute right-4 top-4 z-10">
          <Button
            variant="outline"
            size="sm"
            disabled={isPromoting}
            onClick={() => void handlePromote()}
          >
            {isPromoting ? (
              <Spinner data-icon="inline-start" />
            ) : (
              <TrendingUp data-icon="inline-start" />
            )}
            升级为项目
          </Button>
        </div>
      )}

      <Conversation className="flex-1">
        <ConversationContent className="mx-auto w-full max-w-3xl px-4 py-6">
          {messages.length === 0 ? (
            isLoadingConversations ? (
              <div className="flex h-full items-center justify-center">
                <Spinner className="text-muted-foreground" />
              </div>
            ) : (
              <ChatEmptyState onSuggestion={(s) => void sendMessage(s)} />
            )
          ) : (
            messages.map((message, index) => (
              <MessageRenderer
                key={message.id}
                message={message}
                isLast={index === messages.length - 1}
                isStreaming={isStreaming || isSubmitted}
                onReload={index === messages.length - 1 && message.role === "assistant" ? reload : undefined}
                onOpenApprovals={onOpenApprovals}
              />
            ))
          )}
        </ConversationContent>
        <ConversationScrollButton />
      </Conversation>

      <div className="mx-auto w-full max-w-3xl px-4 pb-4">
        <PromptInput
          onSubmit={handleSubmit}
          className="focus-glow flex w-full flex-col rounded-[20px] border border-[rgba(0,0,0,0.12)] bg-white p-2.5"
          style={{ minHeight: 140, maxHeight: 300 }}
        >
          <PromptInputBody>
            <PromptInputTextarea
              value={input}
              onChange={(e) => setInput(e.currentTarget.value)}
              placeholder="向 SwarmMind 发送消息…"
            />
          </PromptInputBody>
          <PromptInputFooter className="justify-end gap-2">
            <PromptInputTools>
              {isStreaming && (
                <Button type="button" variant="outline" size="sm" onClick={stop}>
                  <SquareIcon className="size-4" />
                  <span>停止</span>
                </Button>
              )}
            </PromptInputTools>
            <PromptInputSubmit
              status={status}
              disabled={!input.trim() || isStreaming || isSubmitted}
            />
          </PromptInputFooter>
        </PromptInput>
      </div>
    </div>
  )
}
