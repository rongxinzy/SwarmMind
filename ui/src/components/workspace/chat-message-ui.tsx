"use client";

import { memo, useCallback, useEffect, useState } from "react";
import { Streamdown } from "streamdown";
import "streamdown/styles.css";
import remarkGfm from "remark-gfm";
import { Check, Copy } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Reasoning, ReasoningContent, ReasoningTrigger } from "@/components/ai-elements/reasoning";
import { cn } from "@/lib/utils";

interface ChatMessageLike {
  id: string;
  role: "user" | "assistant";
  content: string;
  thinking?: string;
  isReasoningStreaming?: boolean;
}

const streamAnimateOptions = {
  animation: "fadeIn" as const,
  duration: 300,
  stagger: 20,
  sep: "word" as const,
};

const streamingRemarkPlugins = [remarkGfm];
const staticRemarkPlugins = [remarkGfm];

export function StreamingDots({ className }: { className?: string }) {
  return (
    <div className={cn("inline-flex items-center", className)} aria-hidden="true">
      {[0, 1, 2].map((index) => (
        <span
          key={index}
          className="chat-stream-dot"
          style={{ animationDelay: `${index * 0.16}s` }}
        />
      ))}
    </div>
  );
}

export function MessageListSkeleton() {
  return (
    <div className="mx-auto flex w-full max-w-[760px] flex-col gap-7 px-6 py-6">
      <div className="flex justify-end">
        <div className="w-full max-w-[420px] space-y-2">
          <div className="skeleton-line h-4 rounded-full" />
          <div className="skeleton-line ml-auto h-4 w-[72%] rounded-full" />
        </div>
      </div>

      <div className="flex justify-start">
        <div className="w-full max-w-[560px] space-y-2">
          <div className="skeleton-line h-4 rounded-full" />
          <div className="skeleton-line h-4 w-[94%] rounded-full" />
          <div className="skeleton-line h-4 w-[68%] rounded-full" />
        </div>
      </div>

      <div className="flex justify-start">
        <div className="w-full max-w-[520px] rounded-2xl border border-[var(--warm-border)] bg-[var(--neutral-150)] px-4 py-4">
          <div className="space-y-2">
            <div className="skeleton-line h-3.5 w-[120px] rounded-full" />
            <div className="skeleton-line h-4 rounded-full" />
            <div className="skeleton-line h-4 w-[88%] rounded-full" />
            <div className="skeleton-line h-4 w-[54%] rounded-full" />
          </div>
        </div>
      </div>
    </div>
  );
}

export const MessageBubble = memo(function MessageBubble({
  message,
  isMessageStreaming = false,
}: {
  message: ChatMessageLike;
  isMessageStreaming?: boolean;
}) {
  const isUser = message.role === "user";
  const hasCodeBlock = !isUser && message.content.includes("```");
  const shouldShowMessageCopy = message.content.trim().length > 0 && (isUser || !hasCodeBlock);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!copied) {
      return;
    }

    const timer = window.setTimeout(() => {
      setCopied(false);
    }, 2000);
    return () => {
      window.clearTimeout(timer);
    };
  }, [copied]);

  const handleCopy = useCallback(async () => {
    if (!message.content.trim()) {
      return;
    }

    try {
      await navigator.clipboard.writeText(message.content);
      setCopied(true);
    } catch (error) {
      console.error("Failed to copy message content:", error);
    }
  }, [message.content]);

  return (
    <div className={cn("group flex w-full", isUser ? "justify-end" : "justify-start md:pr-8")}>
      <div
        className={cn(
          "relative max-w-[90%]",
          isUser
            ? "rounded-[22px] border user-bubble px-[20px] py-[14px] text-[var(--neutral-900)]"
            : "px-1 py-1 md:px-2",
        )}
      >
        {shouldShowMessageCopy ? (
          <div
            className={cn(
              "absolute transition-opacity md:opacity-0 md:group-hover:opacity-100 md:group-focus-within:opacity-100",
              isUser ? "-right-1 -top-1 opacity-100" : "right-2 top-1 opacity-80",
            )}
          >
            <Button
              type="button"
              variant="ghost"
              size="icon-xs"
              onClick={() => {
                void handleCopy();
              }}
              className={cn(
                "h-8 w-8 rounded-[10px] text-muted-foreground md:h-7 md:w-7",
                isUser
                  ? "border border-border bg-card hover:bg-card hover:text-foreground"
                  : "border border-transparent bg-[var(--warm-ivory)] hover:border-[var(--warm-border)] hover:bg-[var(--neutral-150)] hover:text-[var(--neutral-700)]",
              )}
              title={copied ? "已复制" : "复制消息"}
            >
              {copied ? <Check className="size-3 text-[var(--status-done)]" /> : <Copy className="size-3" />}
            </Button>
          </div>
        ) : null}

        {!isUser && message.thinking ? (
          <Reasoning
            isStreaming={message.isReasoningStreaming}
            defaultOpen={true}
            className="mb-4"
          >
            <ReasoningTrigger />
            <ReasoningContent>{message.thinking}</ReasoningContent>
          </Reasoning>
        ) : null}

        {message.content ? (
          isUser ? (
            <div className="whitespace-pre-wrap font-[var(--font-body)] text-[14px] leading-[22px]">{message.content}</div>
          ) : (
            <div className="assistant-markdown prose prose-sm max-w-none px-[12px] py-1 font-[var(--font-body)] text-[14px] leading-[24px] tracking-[-0.003em] text-foreground prose-headings:font-sans prose-pre:my-0 prose-pre:mx-0 prose-pre:rounded-none prose-pre:border-0 prose-pre:bg-transparent prose-pre:p-0 prose-code:font-mono">
              <Streamdown
                mode={isMessageStreaming ? "streaming" : "static"}
                remarkPlugins={isMessageStreaming ? streamingRemarkPlugins : staticRemarkPlugins}
                animated={isMessageStreaming ? streamAnimateOptions : false}
              >
                {message.content}
              </Streamdown>
            </div>
          )
        ) : (
          <div className="flex items-center gap-2 text-[14px] leading-[22px] text-muted-foreground">
            <StreamingDots />
            正在整理回复
          </div>
        )}
      </div>
    </div>
  );
});
