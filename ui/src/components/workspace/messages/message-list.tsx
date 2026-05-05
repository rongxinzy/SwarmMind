import type { Message } from "@langchain/langgraph-sdk";

import { useUpdateSubtask } from "@/core/tasks/context";
import type { Subtask } from "@/core/tasks/types";
import {
  extractContentFromMessage,
  extractPresentFilesFromMessage,
  extractTextFromMessage,
  groupMessages,
  hasContent,
  hasPresentFiles,
  hasReasoning,
  isClarificationToolMessage,
} from "@/core/messages/utils";
import { parseClarificationContent } from "@/core/messages/clarification";
import { cn } from "@/lib/utils";

import { ArtifactFileList } from "../artifacts/artifact-file-list";
import { SubtaskCard } from "./subtask-card";
import { MessageListItem } from "./message-list-item";
import { ClarificationCard } from "./clarification-card";

interface MessageListProps {
  className?: string;
  conversationId?: string;
  messages: Message[];
  isLoading?: boolean;
  onClarificationRespond?: (response: string, toolCallId: string) => void;
}

export function MessageList({
  className,
  conversationId: _conversationId,
  messages,
  isLoading = false,
  onClarificationRespond,
}: MessageListProps) {
  const updateSubtask = useUpdateSubtask();

  return (
    <div className={cn("flex flex-col gap-6", className)}>
      {groupMessages(messages, (group) => {
        // Human messages
        if (group.type === "human" || group.type === "assistant") {
          return group.messages.map((msg) => {
            return (
              <MessageListItem
                key={`${group.id}/${msg.id}`}
                message={msg}
                isLoading={isLoading}
                conversationId={_conversationId}
              />
            );
          });
        }

        // Present files group
        if (group.type === "assistant:present-files") {
          const files: string[] = [];
          for (const message of group.messages) {
            if (hasPresentFiles(message)) {
              const presentFiles = extractPresentFilesFromMessage(message);
              files.push(...presentFiles);
            }
          }
          return (
            <div className="w-full" key={group.id}>
              {group.messages[0] && hasContent(group.messages[0]) && (
                <div className="mb-4">
                  {extractContentFromMessage(group.messages[0])}
                </div>
              )}
              <ArtifactFileList
                files={files}
                conversationId={_conversationId}
              />
            </div>
          );
        }

        // Subagent group - This is where SubtaskCards are rendered
        if (group.type === "assistant:subagent") {
          const tasks = new Set<Subtask>();

          for (const message of group.messages) {
            if (message.type === "ai") {
              // Extract task tool calls from AI messages
              for (const toolCall of message.tool_calls ?? []) {
                if (toolCall.name === "task") {
                  const task: Subtask = {
                    id: toolCall.id!,
                    subagent_type: toolCall.args.subagent_type as string,
                    description: toolCall.args.description as string,
                    prompt: toolCall.args.prompt as string,
                    status: "in_progress",
                  };
                  updateSubtask(task);
                  tasks.add(task);
                }
              }
            } else if (message.type === "tool") {
              // Update task status from tool results
              const taskId = message.tool_call_id;
              if (taskId) {
                const result = extractTextFromMessage(message);
                if (result.startsWith("Task Succeeded. Result:")) {
                  updateSubtask({
                    id: taskId,
                    status: "completed",
                    result: result
                      .split("Task Succeeded. Result:")[1]
                      ?.trim(),
                  });
                } else if (result.startsWith("Task failed.")) {
                  updateSubtask({
                    id: taskId,
                    status: "failed",
                    error: result.split("Task failed.")[1]?.trim(),
                  });
                } else if (result.startsWith("Task timed out")) {
                  updateSubtask({
                    id: taskId,
                    status: "failed",
                    error: result,
                  });
                } else {
                  updateSubtask({
                    id: taskId,
                    status: "in_progress",
                  });
                }
              }
            }
          }

          const results: React.ReactNode[] = [];

          // Render reasoning if any
          for (const message of group.messages.filter(
            (message) => message.type === "ai",
          )) {
            if (hasReasoning(message)) {
              results.push(
                <MessageListItem
                  key={"thinking-group-" + message.id}
                  message={message}
                  isLoading={isLoading}
                  conversationId={_conversationId}
                />,
              );
            }

            // Show task count
            results.push(
              <div
                key="subtask-count"
                className="text-muted-foreground pt-2 text-sm"
              >
                正在执行 {tasks.size} 个子任务...
              </div>,
            );

            // Render SubtaskCards for each task
            const taskIds = message.tool_calls
              ?.filter((toolCall) => toolCall.name === "task")
              .map((toolCall) => toolCall.id);

            for (const taskId of taskIds ?? []) {
              if (taskId) {
                results.push(
                  <SubtaskCard
                    key={"task-group-" + taskId}
                    taskId={taskId}
                    isLoading={isLoading}
                  />,
                );
              }
            }
          }

          return (
            <div
              key={"subtask-group-" + group.id}
              className="relative flex flex-col gap-3"
            >
              {results}
            </div>
          );
        }

        // Clarification group - AI asking user for input
        if (group.type === "assistant:clarification") {
          // Find the ask_clarification tool message
          const toolMessage = group.messages.find(
            (m): m is Message & { type: "tool"; name: string; tool_call_id: string } =>
              m.type === "tool" && isClarificationToolMessage(m)
          );

          if (toolMessage && onClarificationRespond) {
            const parsed = parseClarificationContent(
              typeof toolMessage.content === "string"
                ? toolMessage.content
                : JSON.stringify(toolMessage.content)
            );

            return (
              <ClarificationCard
                key={group.id}
                question={parsed.question}
                context={parsed.context}
                options={parsed.options}
                clarificationType={parsed.clarificationType}
                onRespond={(response) =>
                  { onClarificationRespond(response, toolMessage.tool_call_id); }
                }
              />
            );
          }

          // Fallback: just show the message content
          const message = group.messages[0];
          if (message && hasContent(message)) {
            return (
              <MessageListItem
                key={group.id}
                message={message}
                isLoading={isLoading}
                conversationId={_conversationId}
              />
            );
          }
          return null;
        }

        // Processing group (reasoning + tool calls)
        if (group.type === "assistant:processing") {
          return (
            <MessageListItem
              key={"group-" + group.id}
              message={group.messages[group.messages.length - 1]}
              isLoading={isLoading}
              conversationId={_conversationId}
            />
          );
        }

        return null;
      })}
    </div>
  );
}
