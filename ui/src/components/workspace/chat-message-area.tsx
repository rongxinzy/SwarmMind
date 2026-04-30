import { AnimatePresence, motion } from "framer-motion";
import { toast } from "sonner";
import { Loader2 } from "lucide-react";

import { MessageBubble, SuggestedFollowUps } from "@/components/workspace/chat-message-ui";
import { ClarificationCard } from "@/components/workspace/messages/clarification-card";
import { SubtaskCard } from "@/components/workspace/messages/subtask-card";
import { parseClarificationContent } from "@/core/messages/clarification";
import type { ChatMessage, ChatError } from "@/core/chat/types";
import type { Subtask } from "@/core/tasks/types";
import { Button } from "@/components/ui/button";
import { ERROR_ICON_MAP, ERROR_COPY } from "@/core/chat/mode-config";
import { cn } from "@/lib/utils";

interface PendingClarification {
  id: string;
  content: string;
}

interface ChatMessageAreaProps {
  isLoading: boolean;
  messages: ChatMessage[];
  pendingClarification: PendingClarification | null;
  tasks: Record<string, Subtask>;
  onClarificationRespond: (response: string, toolCallId: string) => void;
  onPendingClarificationHandled: () => void;
  error?: ChatError | null;
  onRetry?: () => void;
  onCopy?: () => void;
  isRetrying?: boolean;
  onSuggestionSelect?: (value: string) => void;
}

function buildSuggestedFollowUps(content: string) {
  const normalized = content.trim();
  if (!normalized) {
    return [
      "你能帮我做些什么？",
      "帮我总结一下今天的重要信息",
      "给我一个适合下一步执行的建议",
    ];
  }

  if (normalized.includes("你好")) {
    return [
      "你能帮我做些什么？",
      "帮我总结一下今天的 AI 新闻",
      "我想了解一下你的功能",
    ];
  }

  if (normalized.includes("报告") || normalized.includes("总结")) {
    return [
      "把这个内容整理成更正式的版本",
      "继续补充 3 条关键行动建议",
      "帮我压缩成一页摘要",
    ];
  }

  return [
    "继续展开这个话题",
    "帮我提炼 3 个重点结论",
    "给我一个适合下一步执行的建议",
  ];
}

function ErrorCard({
  error,
  onRetry,
  onCopy,
  isRetrying,
}: {
  error: ChatError;
  onRetry?: () => void;
  onCopy?: () => void;
  isRetrying?: boolean;
}) {
  const isExhausted = error.retryCount >= 3;
  const Icon = ERROR_ICON_MAP[error.type];
  const copy = isExhausted
    ? { title: "服务暂时不可用", description: "服务暂时不可用，请稍后再试。" }
    : ERROR_COPY[error.type];

  return (
    <motion.div
      initial={{ opacity: 0, translateY: 12, scale: 0.98 }}
      animate={{ opacity: 1, translateY: 0, scale: 1 }}
      exit={{ opacity: 0, translateY: 8, scale: 0.98 }}
      transition={{ duration: 0.26, ease: [0.16, 1, 0.3, 1] }}
      className="flex justify-start"
    >
      <div
        className={cn(
          "w-full max-w-[560px] rounded-[14px] border px-4 py-3.5",
          "bg-[var(--status-blocked-bg)] border-[var(--status-blocked-border)]",
        )}
      >
        <div className="flex items-start gap-3">
          <Icon className="mt-0.5 size-5 shrink-0 text-[var(--status-blocked)]" />
          <div className="min-w-0 flex-1">
            <p className="text-[14px] font-medium text-foreground">
              {copy.title}
            </p>
            <p className="mt-0.5 text-[13px] text-muted-foreground">
              {isExhausted ? copy.description : error.message || copy.description}
            </p>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            {isExhausted ? (
              <Button
                variant="ghost"
                size="sm"
                onClick={onCopy}
                className="text-[12px] text-muted-foreground hover:text-foreground"
              >
                复制问题
              </Button>
            ) : (
              <Button
                variant="secondary"
                size="sm"
                onClick={onRetry}
                disabled={isRetrying}
                className="bg-surface-control text-[12px] text-foreground hover:bg-surface-hover"
              >
                {isRetrying ? (
                  <>
                    <Loader2 className="mr-1 size-3 animate-spin" />
                    重试中
                  </>
                ) : (
                  "重新发送"
                )}
              </Button>
            )}
          </div>
        </div>
      </div>
    </motion.div>
  );
}

export function ChatMessageArea({
  isLoading,
  messages,
  pendingClarification,
  tasks,
  onClarificationRespond,
  onPendingClarificationHandled,
  error,
  onRetry,
  onCopy,
  isRetrying,
  onSuggestionSelect,
}: ChatMessageAreaProps) {
  const taskList = Object.values(tasks);
  const lastAssistantMessage = [...messages]
    .reverse()
    .find((message) => message.role === "assistant" && message.content.trim().length > 0);
  const shouldShowSuggestedFollowUps = Boolean(
    lastAssistantMessage &&
    !isLoading &&
    !pendingClarification &&
    !error,
  );
  const followUps = lastAssistantMessage
    ? buildSuggestedFollowUps(lastAssistantMessage.content)
    : [];

  return (
    <div className="mx-auto flex w-full max-w-[820px] flex-col gap-5 px-6 py-6">
      <AnimatePresence initial={false}>
        {messages.map((message) => {
          const isLastAssistant =
            message.role === "assistant" && lastAssistantMessage?.id === message.id;

          return (
          <motion.div
            key={message.id}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
          >
            <MessageBubble
              key={message.id}
              message={message}
              isMessageStreaming={message.isStreaming || message.isReasoningStreaming}
              showCompletion={Boolean(
                isLastAssistant &&
                !message.isStreaming &&
                !message.isReasoningStreaming &&
                message.content.trim().length > 0,
              )}
            />
            {isLastAssistant && shouldShowSuggestedFollowUps ? (
              <SuggestedFollowUps
                items={followUps}
                onSelect={(value) => {
                  onSuggestionSelect?.(value);
                }}
              />
            ) : null}
          </motion.div>
          );
        })}
      </AnimatePresence>

      {pendingClarification ? (
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
          className="mt-4"
        >
          {(() => {
            try {
              const parsed = parseClarificationContent(pendingClarification.content);
              return (
                <ClarificationCard
                  question={parsed.question}
                  context={parsed.context}
                  options={parsed.options}
                  clarificationType={parsed.clarificationType}
                  onRespond={(response) => {
                    onClarificationRespond(response, pendingClarification.id);
                    onPendingClarificationHandled();
                  }}
                />
              );
            } catch (e) {
              toast.error("AI 澄清请求解析失败，请查看原始消息");
              console.warn("[clarification] parse failed:", e);
              return null;
            }
          })()}
        </motion.div>
      ) : null}

      {taskList.length > 0 ? (
        <div className="mt-4 flex flex-col gap-3">
          <div className="text-sm text-muted-foreground">
            正在执行 {taskList.length} 个子任务...
          </div>
          {taskList.map((task) => (
            <SubtaskCard key={task.id} taskId={task.id} isLoading={isLoading} />
          ))}
        </div>
      ) : null}

      {error ? (
        <ErrorCard
          error={error}
          onRetry={onRetry}
          onCopy={onCopy}
          isRetrying={isRetrying}
        />
      ) : null}

    </div>
  );
}
