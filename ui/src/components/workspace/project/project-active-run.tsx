"use client";

import { useEffect, useRef, useState } from "react";
import { CheckCircle2, XCircle } from "lucide-react";

import { consumeProjectStream } from "@/core/projects/api";
import { cn } from "@/lib/utils";

interface ProjectActiveRunProps {
  projectId: string;
  prompt: string;
  onTerminal: (status: "completed" | "failed", summary?: string) => void;
  onWaitingApproval?: (approvalId: string, capability: string) => void;
}

type RunPhase = "accepted" | "routing" | "running" | "completed" | "failed" | "waiting_approval" | string;

interface StreamEvent {
  type: string;
  phase?: RunPhase;
  label?: string;
  text?: string;
  message?: { content?: string };
  approval_id?: string;
  capability?: string;
  code?: string;
  message_text?: string;
  // error event has a `message` field that is a string, not object
}

function phaseLabel(phase: RunPhase): string {
  switch (phase) {
    case "routing": return "路由中...";
    case "running": return "运行中...";
    case "completed": return "已完成";
    case "failed": return "执行失败";
    default: return "处理中...";
  }
}

export function ProjectActiveRun({
  projectId,
  prompt,
  onTerminal,
  onWaitingApproval,
}: ProjectActiveRunProps) {
  const [phase, setPhase] = useState<RunPhase>("accepted");
  const [accumulatedText, setAccumulatedText] = useState("");
  const [finalContent, setFinalContent] = useState<string | null>(null);
  const [isTerminal, setIsTerminal] = useState(false);
  const [isFailed, setIsFailed] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const calledTerminalRef = useRef(false);

  useEffect(() => {
    let cancelled = false;

    async function run() {
      try {
        await consumeProjectStream<StreamEvent>(
          projectId,
          { content: prompt },
          (event) => {
            if (cancelled) return;

            if (event.type === "status") {
              if (event.phase) setPhase(event.phase);
            } else if (event.type === "content.accumulated") {
              if (event.text !== undefined) {
                setAccumulatedText(event.text);
              }
            } else if (event.type === "assistant_final") {
              const content =
                typeof event.message?.content === "string"
                  ? event.message.content
                  : undefined;
              if (content) setFinalContent(content);
            } else if (event.type === "status.waiting_approval") {
              if (event.approval_id && event.capability) {
                onWaitingApproval?.(event.approval_id, event.capability);
                calledTerminalRef.current = true;
              }
            } else if (event.type === "error") {
              const msg =
                (event as unknown as { message: string }).message ??
                "运行出错";
              setPhase("failed");
              setIsFailed(true);
              setIsTerminal(true);
              if (!calledTerminalRef.current) {
                calledTerminalRef.current = true;
                onTerminal("failed", msg);
              }
            } else if (event.type === "done") {
              setPhase("completed");
              setIsTerminal(true);
              if (!calledTerminalRef.current) {
                calledTerminalRef.current = true;
                onTerminal("completed", finalContent ?? accumulatedText);
              }
            }
          },
        );
        // Stream ended without explicit done event
        if (!cancelled && !calledTerminalRef.current) {
          calledTerminalRef.current = true;
          setPhase("completed");
          setIsTerminal(true);
          onTerminal("completed", finalContent ?? accumulatedText);
        }
      } catch (err) {
        if (!cancelled && !calledTerminalRef.current) {
          calledTerminalRef.current = true;
          const msg = err instanceof Error ? err.message : "连接失败";
          setPhase("failed");
          setIsFailed(true);
          setIsTerminal(true);
          onTerminal("failed", msg);
        }
      }
    }

    void run();

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId, prompt]);

  // Auto-scroll to bottom
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [accumulatedText]);

  const displayText = finalContent ?? accumulatedText;

  return (
    <div className="space-y-3 rounded-xl border border-border bg-card p-4">
      {/* Phase indicator */}
      <div className="flex items-center gap-2">
        {isTerminal ? (
          isFailed ? (
            <XCircle className="size-4 shrink-0 text-red-500" />
          ) : (
            <CheckCircle2 className="size-4 shrink-0 text-green-500" />
          )
        ) : (
          <span className="relative flex size-2 shrink-0">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-blue-400 opacity-75" />
            <span className="relative inline-flex size-2 rounded-full bg-blue-500" />
          </span>
        )}
        <span
          className={cn(
            "text-sm font-medium",
            isFailed
              ? "text-red-600 dark:text-red-400"
              : isTerminal
                ? "text-green-600 dark:text-green-400"
                : "text-blue-600 dark:text-blue-400",
          )}
        >
          {phaseLabel(phase)}
        </span>
      </div>

      {/* Accumulated content */}
      {displayText && (
        <div
          ref={scrollRef}
          className="max-h-64 overflow-y-auto rounded-md bg-muted/50 p-3 text-sm text-foreground/90 whitespace-pre-wrap font-mono"
        >
          {displayText}
        </div>
      )}
    </div>
  );
}
