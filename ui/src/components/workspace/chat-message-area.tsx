import { AnimatePresence, motion } from "framer-motion";
import { toast } from "sonner";

import { MessageBubble, StreamingDots } from "@/components/workspace/chat-message-ui";
import { ClarificationCard } from "@/components/workspace/messages/clarification-card";
import { SubtaskCard } from "@/components/workspace/messages/subtask-card";
import { parseClarificationContent } from "@/core/messages/clarification";
import type { ChatMessage } from "@/core/chat/types";
import type { Subtask } from "@/core/tasks/types";

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
}

export function ChatMessageArea({
  isLoading,
  messages,
  pendingClarification,
  tasks,
  onClarificationRespond,
  onPendingClarificationHandled,
}: ChatMessageAreaProps) {
  const taskList = Object.values(tasks);

  return (
    <div className="mx-auto flex w-full max-w-[760px] flex-col gap-5 px-6 py-6">
      <AnimatePresence initial={false}>
        {messages.map((message) => {
          if (
            message.role === "assistant" &&
            (message.content.includes("需要") ||
              message.content.includes("?") ||
              message.content.includes("选择") ||
              message.content.includes("确认"))
          ) {
            try {
              const parsed = parseClarificationContent(message.content);
              if (parsed.question && parsed.clarificationType) {
                return (
                  <ClarificationCard
                    key={message.id}
                    question={parsed.question}
                    context={parsed.context}
                    options={parsed.options}
                    clarificationType={parsed.clarificationType}
                    onRespond={(response) => {
                      onClarificationRespond(response, message.id);
                    }}
                  />
                );
              }
            } catch (e) {
              toast.error("AI 澄清请求解析失败，请查看原始消息");
              console.warn("[clarification] parse failed:", e);
            }
          }

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
              />
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

      {isLoading &&
        !messages.some((message) => message.content.trim().length > 0 && message.role === "assistant") && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.2 }}
            className="flex justify-start"
          >
            <div className="flex items-center gap-2 rounded-xl border border-[var(--warm-border)] bg-[var(--neutral-150)] px-4 py-2">
              <StreamingDots />
              <span className="text-[13px] text-muted-foreground">正在生成回复</span>
            </div>
          </motion.div>
        )}
    </div>
  );
}
