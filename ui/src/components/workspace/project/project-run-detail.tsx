"use client";

import { useEffect, useState } from "react";
import { X, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { getRunEvents } from "@/core/projects/api";
import type { Run, RunEvent } from "@/core/projects/types";
import { cn } from "@/lib/utils";

interface ProjectRunDetailProps {
  projectId: string;
  run: Run;
  onClose: () => void;
}

function eventTypeLabel(eventType: string): string {
  switch (eventType) {
    case "run.started": return "运行开始";
    case "run.completed": return "运行完成";
    case "run.failed": return "运行失败";
    case "approval.decided": return "审批决定";
    default: return eventType;
  }
}

function formatTime(isoString: string): string {
  const date = new Date(isoString);
  if (Number.isNaN(date.getTime())) return isoString;
  return new Intl.DateTimeFormat("zh-CN", {
    month: "numeric",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(date);
}

export function ProjectRunDetail({ projectId, run, onClose }: ProjectRunDetailProps) {
  const [events, setEvents] = useState<RunEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    getRunEvents(projectId, run.run_id)
      .then((items) => {
        if (!cancelled) {
          setEvents(items);
          setLoading(false);
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "加载失败");
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [projectId, run.run_id]);

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40 bg-black/20"
        onClick={onClose}
      />

      {/* Panel */}
      <div className="fixed inset-y-0 right-0 z-50 flex w-full max-w-md flex-col border-l border-border bg-background shadow-xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-border px-4 py-3">
          <div className="min-w-0">
            <h2 className="truncate text-sm font-semibold text-foreground">运行详情</h2>
            <p className="mt-0.5 truncate text-[11px] text-muted-foreground">
              {run.goal ?? run.run_id.slice(0, 12)}
            </p>
          </div>
          <Button
            variant="ghost"
            size="icon-sm"
            onClick={onClose}
            className="shrink-0 rounded-lg"
            title="关闭"
          >
            <X className="size-4" />
          </Button>
        </div>

        {/* Run meta */}
        <div className="flex gap-4 border-b border-border px-4 py-3 text-xs text-muted-foreground">
          <span>状态: <span className="text-foreground">{run.status}</span></span>
          {run.started_at && (
            <span>开始: <span className="text-foreground">{formatTime(run.started_at)}</span></span>
          )}
        </div>

        {/* Events */}
        <div className="flex-1 overflow-y-auto px-4 py-4">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="size-5 animate-spin text-muted-foreground" />
            </div>
          ) : error ? (
            <p className="text-sm text-destructive">{error}</p>
          ) : events.length === 0 ? (
            <p className="text-sm text-muted-foreground">此次运行暂无事件记录</p>
          ) : (
            <ol className="relative space-y-4 border-l border-border pl-4">
              {events.map((evt) => (
                <li key={evt.audit_id} className="relative">
                  {/* Timeline dot */}
                  <span className="absolute -left-[21px] top-0.5 flex size-2.5 items-center justify-center">
                    <span className="size-2 rounded-full border border-border bg-background" />
                  </span>

                  <div className="space-y-0.5">
                    <div className="flex items-baseline gap-2">
                      <span
                        className={cn(
                          "text-xs font-medium",
                          evt.audit_type === "run.failed"
                            ? "text-red-600 dark:text-red-400"
                            : evt.audit_type === "run.completed"
                              ? "text-green-600 dark:text-green-400"
                              : "text-foreground",
                        )}
                      >
                        {eventTypeLabel(evt.audit_type)}
                      </span>
                      <span className="text-[10px] text-muted-foreground">
                        {formatTime(evt.created_at)}
                      </span>
                    </div>

                    {evt.decision && (
                      <p className="text-xs text-muted-foreground">
                        决定: <span className="text-foreground">{evt.decision}</span>
                      </p>
                    )}
                    {evt.reason && (
                      <p className="text-xs text-muted-foreground">
                        原因: {evt.reason}
                      </p>
                    )}
                  </div>
                </li>
              ))}
            </ol>
          )}
        </div>
      </div>
    </>
  );
}
