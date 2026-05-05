"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Bot,
  FileText,
  GitBranch,
  ListTodo,
  MessageSquare,
  RefreshCw,
  Wrench,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface ToolCall {
  id: string | null;
  name: string | null;
  args: string;
}

interface TodoItem {
  description: string;
  status: string;
}

interface TraceEvent {
  id: number;
  type:
    | "user_input"
    | "assistant_response"
    | "subagent_dispatch"
    | "tool_execution"
    | "artifact_created"
    | "todos_updated";
  agent_id: string;
  agent_status: string;
  content: string;
  timestamp: string;
  tool_calls?: ToolCall[];
  result?: string;
  artifact_path?: string;
  reasoning?: string;
  todo_items?: TodoItem[];
  todos_count?: number;
}

interface TraceData {
  thread_id: string;
  status: string;
  events: TraceEvent[];
  summary: string;
  checkpoint_count: number;
}

interface TracePanelProps {
  conversationId: string;
}

const EVENT_CONFIG = {
  user_input: {
    icon: MessageSquare,
    label: "用户输入",
    color: "text-blue-500",
    bg: "bg-blue-50 dark:bg-blue-950/30",
    border: "border-blue-200 dark:border-blue-800",
  },
  assistant_response: {
    icon: Bot,
    label: "助手回复",
    color: "text-green-500",
    bg: "bg-green-50 dark:bg-green-950/30",
    border: "border-green-200 dark:border-green-800",
  },
  subagent_dispatch: {
    icon: GitBranch,
    label: "工具调用",
    color: "text-purple-500",
    bg: "bg-purple-50 dark:bg-purple-950/30",
    border: "border-purple-200 dark:border-purple-800",
  },
  tool_execution: {
    icon: Wrench,
    label: "工具执行",
    color: "text-orange-500",
    bg: "bg-orange-50 dark:bg-orange-950/30",
    border: "border-orange-200 dark:border-orange-800",
  },
  artifact_created: {
    icon: FileText,
    label: "产物生成",
    color: "text-teal-500",
    bg: "bg-teal-50 dark:bg-teal-950/30",
    border: "border-teal-200 dark:border-teal-800",
  },
  todos_updated: {
    icon: ListTodo,
    label: "计划更新",
    color: "text-amber-500",
    bg: "bg-amber-50 dark:bg-amber-950/30",
    border: "border-amber-200 dark:border-amber-800",
  },
} as const;

function formatTime(ts: string): string {
  try {
    return new Date(ts).toLocaleTimeString("zh-CN", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  } catch {
    return "";
  }
}

function TraceEventCard({ event }: { event: TraceEvent }) {
  const [expanded, setExpanded] = useState(false);
  const config = EVENT_CONFIG[event.type] ?? EVENT_CONFIG.assistant_response;
  const Icon = config.icon;

  const hasDetail =
    (event.tool_calls && event.tool_calls.length > 0) ||
    event.result ||
    event.reasoning ||
    (event.todo_items && event.todo_items.length > 0);

  return (
    <div className="flex gap-3">
      <div className="flex flex-col items-center">
        <div
          className={cn(
            "flex size-7 shrink-0 items-center justify-center rounded-full border",
            config.bg,
            config.border,
          )}
        >
          <Icon className={cn("size-3.5", config.color)} />
        </div>
        <div className="mt-1 w-px flex-1 bg-border/60" />
      </div>

      <div className="mb-3 min-w-0 flex-1 pb-1">
        <div className="flex items-center gap-2">
          <span className={cn("text-xs font-medium", config.color)}>
            {config.label}
          </span>
          {event.agent_id !== "user" && event.agent_id !== "system" && (
            <span className="rounded bg-muted px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground">
              {event.agent_id}
            </span>
          )}
          <span className="ml-auto shrink-0 text-[10px] text-muted-foreground/70">
            {formatTime(event.timestamp)}
          </span>
        </div>

        <p className="mt-1 line-clamp-3 text-xs leading-relaxed text-foreground/80">
          {event.content}
        </p>

        {hasDetail && (
          <button
            onClick={() => {
              setExpanded((v) => !v);
            }}
            className="mt-1.5 text-[10px] text-muted-foreground underline-offset-2 hover:text-foreground hover:underline"
          >
            {expanded ? "收起详情" : "展开详情"}
          </button>
        )}

        {expanded && (
          <div className="mt-2 space-y-2">
            {event.tool_calls?.map((tc, i) => (
              <div key={i} className="rounded-md border bg-muted/50 p-2">
                <p className="mb-1 font-mono text-[10px] font-semibold text-purple-600 dark:text-purple-400">
                  {tc.name ?? "unknown"}
                </p>
                <pre className="whitespace-pre-wrap break-all font-mono text-[9px] text-muted-foreground">
                  {tc.args}
                </pre>
              </div>
            ))}

            {event.result && (
              <div className="rounded-md border bg-muted/50 p-2">
                <p className="mb-1 text-[10px] font-semibold text-muted-foreground">
                  执行结果
                </p>
                <pre className="whitespace-pre-wrap break-all font-mono text-[9px] text-foreground/70">
                  {event.result}
                </pre>
              </div>
            )}

            {event.reasoning && (
              <div className="rounded-md border border-dashed bg-muted/30 p-2">
                <p className="mb-1 text-[10px] font-semibold text-muted-foreground">
                  推理过程
                </p>
                <p className="text-[10px] leading-relaxed text-foreground/60">
                  {event.reasoning}
                </p>
              </div>
            )}

            {event.todo_items && event.todo_items.length > 0 && (
              <div className="rounded-md border bg-muted/50 p-2">
                <p className="mb-1.5 text-[10px] font-semibold text-muted-foreground">
                  任务计划 ({event.todos_count ?? event.todo_items.length})
                </p>
                <ul className="space-y-1">
                  {event.todo_items.map((todo, i) => (
                    <li key={i} className="flex items-start gap-1.5">
                      <span
                        className={cn(
                          "mt-0.5 size-2 shrink-0 rounded-full border",
                          todo.status === "done"
                            ? "border-green-400 bg-green-400"
                            : "border-muted-foreground",
                        )}
                      />
                      <span className="text-[10px] leading-relaxed text-foreground/70">
                        {todo.description}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export function TracePanel({ conversationId }: TracePanelProps) {
  const [trace, setTrace] = useState<TraceData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchTrace = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`/api/conversations/${conversationId}/trace`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = (await res.json()) as { trace: TraceData | null };
      setTrace(data.trace ?? null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "加载失败");
    } finally {
      setLoading(false);
    }
  }, [conversationId]);

  useEffect(() => {
    void fetchTrace();
  }, [fetchTrace]);

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="flex flex-col items-center gap-3 text-center">
          <RefreshCw className="size-5 animate-spin text-muted-foreground" />
          <p className="text-xs text-muted-foreground">加载执行轨迹...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-3 p-6 text-center">
        <p className="text-xs text-destructive">{error}</p>
        <Button
          variant="outline"
          size="sm"
          onClick={() => {
            void fetchTrace();
          }}
        >
          重试
        </Button>
      </div>
    );
  }

  if (!trace || trace.status === "empty" || trace.events.length === 0) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-3 p-6 text-center">
        <GitBranch className="size-10 text-muted-foreground/40" />
        <p className="text-xs font-medium text-muted-foreground">暂无执行轨迹</p>
        <p className="max-w-[180px] text-[11px] text-muted-foreground/60">
          当 Agent 开始执行后，轨迹将显示在这里
        </p>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => {
            void fetchTrace();
          }}
          className="mt-1 gap-1.5 text-xs"
        >
          <RefreshCw className="size-3" />
          刷新
        </Button>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      <div className="border-b px-4 py-2">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs text-muted-foreground">{trace.summary}</p>
          </div>
          <Button
            variant="ghost"
            size="icon-sm"
            onClick={() => {
              void fetchTrace();
            }}
            title="刷新轨迹"
          >
            <RefreshCw className="size-3.5" />
          </Button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        <div className="flex flex-col">
          {trace.events.map((event) => (
            <TraceEventCard key={event.id} event={event} />
          ))}
          <div className="mt-1 flex justify-center">
            <span
              className={cn(
                "rounded-full px-2 py-0.5 text-[10px] font-medium",
                trace.status === "completed"
                  ? "bg-green-100 text-green-700 dark:bg-green-950/40 dark:text-green-400"
                  : trace.status === "running"
                    ? "bg-blue-100 text-blue-700 dark:bg-blue-950/40 dark:text-blue-400"
                    : "bg-muted text-muted-foreground",
              )}
            >
              {trace.status === "completed"
                ? "执行完成"
                : trace.status === "running"
                  ? "执行中"
                  : trace.status === "delegating"
                    ? "子代理协作中"
                    : trace.status === "waiting"
                      ? "等待输入"
                      : "未知状态"}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
