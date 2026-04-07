"use client";

import { CheckCircleIcon, ChevronUp, ClipboardListIcon, Loader2Icon, XCircleIcon } from "lucide-react";
import { useMemo, useState } from "react";

import { Shimmer } from "@/components/ai-elements/shimmer";
import { Button } from "@/components/ui/button";
import {
  ChainOfThought,
  ChainOfThoughtContent,
  ChainOfThoughtStep,
} from "@/components/ai-elements/chain-of-thought";
import { useSubtask } from "@/core/tasks/context";
import { explainLastToolCall } from "@/core/tools/utils";
import { hasToolCalls } from "@/core/messages/utils";
import { cn } from "@/lib/utils";

// Re-export types for compatibility
export type { Subtask } from "@/core/tasks/types";

export function SubtaskCard({
  className,
  taskId,
  isLoading: _isLoading,
}: {
  className?: string;
  taskId: string;
  isLoading?: boolean;
}) {
  const [collapsed, setCollapsed] = useState(true);
  const task = useSubtask(taskId)!;

  const icon = useMemo(() => {
    if (task.status === "completed") {
      return <CheckCircleIcon className="size-4 text-green-500" />;
    } else if (task.status === "failed") {
      return <XCircleIcon className="size-4 text-red-500" />;
    } else if (task.status === "in_progress") {
      return <Loader2Icon className="size-4 animate-spin text-primary" />;
    }
  }, [task.status]);

  const statusLabel = useMemo(() => {
    switch (task.status) {
      case "completed":
        return "已完成";
      case "failed":
        return "失败";
      case "in_progress":
      default:
        return "进行中";
    }
  }, [task.status]);

  return (
    <ChainOfThought
      className={cn(
        "relative w-full gap-2 rounded-lg border bg-card py-0 overflow-hidden",
        task.status === "in_progress" && "border-primary/30",
        className
      )}
      open={!collapsed}
    >
      {/* Ambient glow effect for in-progress tasks */}
      {task.status === "in_progress" && (
        <div className="absolute inset-0 -z-10 bg-gradient-to-r from-primary/5 via-primary/10 to-primary/5 animate-pulse" />
      )}

      <div className="flex w-full flex-col rounded-lg">
        <div className="flex w-full items-center justify-between p-0.5">
          <Button
            className="w-full items-start justify-start text-left hover:bg-transparent"
            variant="ghost"
            onClick={() => setCollapsed(!collapsed)}
          >
            <div className="flex w-full items-center justify-between">
              <ChainOfThoughtStep
                className="font-normal"
                label={
                  task.status === "in_progress" ? (
                    <Shimmer duration={3} spread={3}>
                      {task.description}
                    </Shimmer>
                  ) : (
                    task.description
                  )
                }
                icon={<ClipboardListIcon className="size-4" />}
              />
              <div className="flex items-center gap-2">
                {collapsed && (
                  <div
                    className={cn(
                      "flex items-center gap-1.5 text-xs font-normal",
                      task.status === "failed" ? "text-red-500" : "text-muted-foreground"
                    )}
                  >
                    {icon}
                    <span className="max-w-[200px] truncate">
                      {task.status === "in_progress" && task.latestMessage && hasToolCalls(task.latestMessage)
                        ? explainLastToolCall(task.latestMessage)
                        : statusLabel}
                    </span>
                  </div>
                )}
                <ChevronUp
                  className={cn(
                    "size-4 text-muted-foreground transition-transform duration-200",
                    !collapsed ? "" : "rotate-180"
                  )}
                />
              </div>
            </div>
          </Button>
        </div>

        <ChainOfThoughtContent className="px-4 pb-4">
          {/* Task Prompt */}
          {task.prompt && (
            <ChainOfThoughtStep
              label={<span className="text-muted-foreground">任务指令</span>}
              icon={<ClipboardListIcon className="size-4 text-muted-foreground" />}
            >
              <div className="mt-2 rounded-md bg-secondary p-3 text-sm text-muted-foreground whitespace-pre-wrap">
                {task.prompt}
              </div>
            </ChainOfThoughtStep>
          )}

          {/* Current Tool Call */}
          {task.status === "in_progress" && task.latestMessage && hasToolCalls(task.latestMessage) && (
            <ChainOfThoughtStep
              label={<span className="text-muted-foreground">{explainLastToolCall(task.latestMessage)}</span>}
              icon={<Loader2Icon className="size-4 animate-spin text-primary" />}
            >
              <div className="mt-2 font-mono text-xs text-muted-foreground">
                {task.latestMessage.tool_calls?.slice(-1).map((toolCall) => (
                  <div key={toolCall.id} className="space-y-1">
                    {Object.entries(toolCall.args as Record<string, unknown>)
                      .filter(([key]) => key !== "description")
                      .map(([key, value]) => (
                        <div key={key} className="truncate">
                          <span className="text-primary/60">{key}:</span>{" "}
                          {typeof value === "string" ? value : JSON.stringify(value)}
                        </div>
                      ))}
                  </div>
                ))}
              </div>
            </ChainOfThoughtStep>
          )}

          {/* Completed Result */}
          {task.status === "completed" && (
            <>
              <ChainOfThoughtStep
                label={<span className="text-green-600">{statusLabel}</span>}
                icon={<CheckCircleIcon className="size-4 text-green-500" />}
              />
              {task.result && (
                <ChainOfThoughtStep
                  label={<span className="text-muted-foreground">执行结果</span>}
                >
                  <div className="mt-2 rounded-md bg-secondary p-3 text-sm whitespace-pre-wrap max-h-48 overflow-y-auto">
                    {task.result}
                  </div>
                </ChainOfThoughtStep>
              )}
            </>
          )}

          {/* Failed Error */}
          {task.status === "failed" && (
            <ChainOfThoughtStep
              label={<span className="text-red-500">{task.error || "任务执行失败"}</span>}
              icon={<XCircleIcon className="size-4 text-red-500" />}
            />
          )}
        </ChainOfThoughtContent>
      </div>
    </ChainOfThought>
  );
}
