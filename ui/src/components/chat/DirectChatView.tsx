"use client"

import { useCallback, useEffect, useRef, useState } from "react"
import { Spinner } from "@/components/ui/spinner"
import { ScrollArea } from "@/components/ui/scroll-area"
import { useDirectChat } from "@/hooks/useDirectChat"
import { ChatInputBox } from "./ChatInputBox"
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

  const isEmpty = messages.length === 0

  return (
    <div className="relative flex min-w-0 flex-1 flex-col overflow-hidden bg-[#fbfbfa]">
      <div className="flex flex-1 flex-col overflow-hidden">
        {isEmpty ? (
          <div className="flex flex-1 flex-col items-center justify-center px-6 pb-32">
            <div className="w-full max-w-[720px]">
              <div className="mb-8 text-center">
                <h1 className="text-2xl font-medium text-[#1a1a1a]">有什么可以帮你的？</h1>
                <p className="mt-3 text-sm leading-6 text-[#5d5d5d]">
                  Chat 模式直接连接模型，不经过 Agent 工作流。
                </p>
              </div>
              <ChatInputBox
                value={input}
                onValueChange={setInput}
                status={status}
                models={models}
                selectedModelId={selectedModelId}
                isLoadingModels={isLoadingModels}
                placement="empty"
                autoFocus
                onModelChange={selectModel}
                onSubmit={handleSubmit}
                onStop={stop}
              />
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

      {!isEmpty && (
        <div className="px-4 pb-4 pt-3">
          <div className="mx-auto w-full max-w-3xl">
            <ChatInputBox
              value={input}
              onValueChange={setInput}
              status={status}
              models={models}
              selectedModelId={selectedModelId}
              isLoadingModels={isLoadingModels}
              placement="docked"
              onModelChange={selectModel}
              onSubmit={handleSubmit}
              onStop={stop}
            />
          </div>
        </div>
      )}
    </div>
  )
}
