"use client";

import { memo, useCallback, useEffect, useState } from "react";
import { Streamdown } from "streamdown";
import "streamdown/styles.css";
import remarkGfm from "remark-gfm";
import { ArrowRight, Check, Copy, MessageCircle, Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Reasoning, ReasoningContent, ReasoningTrigger } from "@/components/ai-elements/reasoning";
import { cn } from "@/lib/utils";

interface ChatMessageLike {
  id: string;
  role: "user" | "assistant";
  content: string;
  created_at?: string;
  thinking?: string;
  isReasoningStreaming?: boolean;
}

const streamAnimateOptions = {
  animation: "fadeIn" as const,
  duration: 80,
  stagger: 3,
  sep: "char" as const,
};

const streamingRemarkPlugins = [remarkGfm];
const staticRemarkPlugins = [remarkGfm];

function formatMessageTime(createdAt?: string) {
  const normalizedCreatedAt = createdAt
    ? /(?:Z|[+-]\d{2}:\d{2})$/.test(createdAt)
      ? createdAt
      : `${createdAt}Z`
    : undefined;
  const date = normalizedCreatedAt ? new Date(normalizedCreatedAt) : new Date();
  if (Number.isNaN(date.getTime())) {
    return "";
  }
  return date.toLocaleTimeString("zh-CN", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
    timeZone: "Asia/Shanghai",
  });
}

export function StreamingDots({ className }: { className?: string }) {
  return (
    <div className={cn("inline-flex items-center", className)} aria-hidden="true">
      {[0, 1, 2].map((index) => (
        <span
          key={index}
          className="chat-stream-dot text-[1em] leading-none"
          style={{ animationDelay: `${index * 0.16}s` }}
        >
          .
        </span>
      ))}
    </div>
  );
}

export function MessageListSkeleton() {
  return (
    <div className="mx-auto flex w-full max-w-[820px] flex-col gap-7 px-6 py-6">
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
        <div className="w-full max-w-[520px] rounded-xl border border-border bg-surface-hover px-4 py-4">
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

export function SuggestedFollowUps({
  items,
  onSelect,
}: {
  items: string[];
  onSelect: (value: string) => void;
}) {
  return (
    <div className="mt-5 border-t border-border/80 pt-4 pl-4">
      <p className="text-[13px] font-medium text-muted-foreground">推荐追问</p>
      <div className="mt-2 overflow-hidden rounded-[18px] border border-border/70 bg-card">
        {items.map((item, index) => (
          <button
            key={item}
            type="button"
            onClick={() => { onSelect(item); }}
            className={cn(
              "flex w-full items-center gap-3 px-4 py-3 text-left transition-colors hover:bg-surface-hover",
              index !== items.length - 1 && "border-b border-border/70",
            )}
          >
            <MessageCircle className="size-4 shrink-0 text-muted-foreground" />
            <span className="min-w-0 flex-1 text-[15px] text-foreground">{item}</span>
            <ArrowRight className="size-4 shrink-0 text-muted-foreground" />
          </button>
        ))}
      </div>
    </div>
  );
}

export const MessageBubble = memo(function MessageBubble({
  message,
  isMessageStreaming = false,
  showCompletion = false,
}: {
  message: ChatMessageLike;
  isMessageStreaming?: boolean;
  showCompletion?: boolean;
}) {
  const isUser = message.role === "user";
  const [copied, setCopied] = useState(false);
  const formattedTime = formatMessageTime(message.created_at);

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
    <div className={cn("group flex w-full", isUser ? "justify-end" : "justify-start")}>
      <div
        className={cn(
          "relative",
          isUser
            ? "max-w-[260px] py-[6px] text-foreground"
            : "w-full max-w-none py-2 pl-4",
        )}
      >
        {!isUser ? (
          <div className="mb-4 flex flex-col items-start gap-3">
            <div className="flex flex-col items-start gap-2">
              <div className="flex items-center gap-3">
                <div className="flex size-9 items-center justify-center rounded-[14px] border border-border bg-surface-muted text-foreground">
                  <Sparkles className="size-4" />
                </div>
                <p className="text-[15px] font-medium text-foreground">SwarmMind</p>
              </div>
              {!message.content ? (
                <div className="flex items-center gap-1 text-[14px] text-muted-foreground">
                  <span>SwarmMind 正在思考中</span>
                  <StreamingDots />
                </div>
              ) : null}
            </div>
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
            <div className="flex flex-col items-end gap-2">
              <div className="rounded-[20px] border border-border bg-card px-[18px] py-[14px] shadow-[0_2px_8px_rgba(24,24,27,0.04)]">
                <div className="whitespace-pre-wrap text-[14px] leading-[22px]">{message.content}</div>
              </div>
              <div className="mt-[-2px] flex items-center gap-2 pr-1 text-[12px] text-muted-foreground">
                <Button
                  type="button"
                  variant="ghost"
                  size="icon-xs"
                  onClick={() => {
                    void handleCopy();
                  }}
                  className="h-7 w-7 rounded-[10px] border border-transparent bg-transparent text-muted-foreground hover:bg-surface-hover hover:text-foreground"
                  title={copied ? "已复制" : "复制消息"}
                >
                  {copied ? <Check className="size-3 text-[var(--status-done)]" /> : <Copy className="size-3" />}
                </Button>
                {formattedTime ? <span>{formattedTime}</span> : null}
              </div>
            </div>
          ) : (
            <div className="assistant-markdown prose prose-sm max-w-none py-1 text-[15px] leading-[28px] text-foreground prose-headings:font-sans prose-pre:my-0 prose-pre:mx-0 prose-pre:rounded-none prose-pre:border-0 prose-pre:bg-transparent prose-pre:p-0 prose-code:font-mono">
              <Streamdown
                mode={isMessageStreaming ? "streaming" : "static"}
                remarkPlugins={isMessageStreaming ? streamingRemarkPlugins : staticRemarkPlugins}
                animated={isMessageStreaming ? streamAnimateOptions : false}
              >
                {message.content}
              </Streamdown>
            </div>
          )
        ) : null}

        {!isUser && showCompletion ? (
          <div className="mt-5 flex items-center gap-2 border-t border-border/80 pt-4 text-[14px] font-medium text-[var(--status-done)]">
            <Check className="size-4" />
            <span>任务已完成</span>
          </div>
        ) : null}
      </div>
    </div>
  );
});
