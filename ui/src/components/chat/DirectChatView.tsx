"use client"

import { useCallback, useEffect, useRef, useState } from "react"
import { Send, Square } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Spinner } from "@/components/ui/spinner"
import { Textarea } from "@/components/ui/textarea"
import { ScrollArea } from "@/components/ui/scroll-area"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { useDirectChat } from "@/hooks/useDirectChat"
import { toast } from "sonner"
import { cn } from "@/lib/utils"

interface DirectChatViewProps {
  conversationId?: string
  onConversationCreated?: (id: string, title: string) => void
}

export function DirectChatView({ conversationId, onConversationCreated }: DirectChatViewProps) {
  const {
    messages,
    status,
    error,
    models,
    selectedModelId,
    isLoadingModels,
    selectModel,
    sendMessage,
    stop,
  } = useDirectChat({ conversationId, onConversationCreated })
  const [input, setInput] = useState("")
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const scrollRef = useRef<HTMLDivElement>(null)
  const isStreaming = status === "streaming"

  useEffect(() => {
    if (error) {
      toast.error(error)
    }
  }, [error])

  useEffect(() => {
    const el = scrollRef.current
    if (!el) return
    el.scrollTop = el.scrollHeight
  }, [messages])

  const handleSubmit = useCallback(async () => {
    const text = input.trim()
    if (!text || isStreaming) return
    setInput("")
    await sendMessage(text)
  }, [input, isStreaming, sendMessage])

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault()
        void handleSubmit()
      }
    },
    [handleSubmit],
  )

  const selectedModel = models.find((m) => m.id === selectedModelId)

  return (
    <div className="relative flex min-w-0 flex-1 flex-col overflow-hidden bg-[#fbfbfa]">
      <div className="flex flex-1 flex-col overflow-hidden">
        {messages.length === 0 ? (
          <div className="flex flex-1 flex-col items-center justify-center px-6 pb-32">
            <div className="max-w-md text-center">
              <h1 className="text-2xl font-medium text-[#1a1a1a]">有什么可以帮你的？</h1>
              <p className="mt-3 text-sm leading-6 text-[#5d5d5d]">
                Chat 模式直接连接模型，不经过 Agent 工作流。
              </p>
            </div>
          </div>
        ) : (
          <ScrollArea ref={scrollRef} className="flex-1 px-4">
            <div className="mx-auto max-w-[820px] py-8">
              {messages.map((message) => (
                <div
                  key={message.id}
                  className={cn(
                    "mb-6 flex",
                    message.role === "user" ? "justify-end" : "justify-start",
                  )}
                >
                  <div
                    className={cn(
                      "max-w-[85%] whitespace-pre-wrap rounded-2xl px-5 py-3 text-sm leading-6",
                      message.role === "user"
                        ? "bg-[#1a1a1a] text-white"
                        : "border border-[#e8e8e8] bg-white text-[#1a1a1a] shadow-sm",
                    )}
                  >
                    {message.content}
                  </div>
                </div>
              ))}
              {isStreaming && !messages.some((m) => m.id === "assistant-streaming") && (
                <div className="mb-6 flex justify-start">
                  <div className="rounded-2xl border border-[#e8e8e8] bg-white px-5 py-3 shadow-sm">
                    <Spinner className="size-4 text-muted-foreground" />
                  </div>
                </div>
              )}
            </div>
          </ScrollArea>
        )}
      </div>

      <div className="border-t border-[#e8e8e8] bg-white px-4 pb-4 pt-3">
        <div className="mx-auto flex max-w-3xl flex-col gap-2">
          <div className="flex items-center gap-2">
            <Select
              value={selectedModelId ?? undefined}
              onValueChange={(value) => value && selectModel(value)}
              disabled={isLoadingModels || models.length === 0}
            >
              <SelectTrigger className="h-8 w-auto min-w-[140px] border-[#e8e8e8] text-xs">
                <SelectValue placeholder={isLoadingModels ? "加载中..." : "选择模型"} />
              </SelectTrigger>
              <SelectContent>
                {models.map((model) => (
                  <SelectItem key={model.id} value={model.id} className="text-xs">
                    {model.display_name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {selectedModel && (
              <span className="text-xs text-muted-foreground">
                {selectedModel.supports_thinking ? "支持推理" : "直出模式"}
              </span>
            )}
          </div>

          <div className="relative flex items-end gap-2 rounded-2xl border border-[#e8e8e8] bg-white p-2 shadow-sm">
            <Textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="输入消息..."
              rows={1}
              className="min-h-[44px] resize-none border-0 bg-transparent px-3 py-2.5 text-sm shadow-none focus-visible:ring-0"
            />
            <Button
              size="icon"
              className="mb-0.5 size-9 shrink-0 rounded-xl"
              disabled={!isStreaming && !input.trim()}
              onClick={() => {
                if (isStreaming) {
                  stop()
                } else {
                  void handleSubmit()
                }
              }}
              aria-label={isStreaming ? "停止" : "发送"}
            >
              {isStreaming ? <Square className="size-4" /> : <Send className="size-4" />}
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}
