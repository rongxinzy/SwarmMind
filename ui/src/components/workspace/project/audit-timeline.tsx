"use client";

import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";

import { getProjectAuditLogs } from "@/core/projects/api";
import type { RunEvent } from "@/core/projects/types";
import { cn } from "@/lib/utils";

interface AuditTimelineProps {
  projectId: string;
}

function eventLabel(auditType: string): string {
  const map: Record<string, string> = {
    "run.started": "运行开始",
    "run.completed": "运行完成",
    "run.failed": "运行失败",
    "run.resumed": "运行恢复",
    "task.created": "任务创建",
    "task.started": "任务开始",
    "task.completed": "任务完成",
    "task.failed": "任务失败",
    "task.blocked": "任务阻塞",
    "approval.requested": "审批请求",
    "approval.decided": "审批决定",
    "approval.approved": "审批通过",
    "approval.rejected": "审批拒绝",
  };
  return map[auditType] ?? auditType;
}

function eventDotClass(auditType: string): string {
  if (auditType.includes("failed") || auditType.includes("rejected")) {
    return "bg-red-400 dark:bg-red-600";
  }
  if (auditType.includes("completed") || auditType.includes("approved") || auditType.includes("resumed")) {
    return "bg-green-400 dark:bg-green-600";
  }
  if (auditType.includes("approval") || auditType.includes("blocked")) {
    return "bg-amber-400 dark:bg-amber-600";
  }
  return "bg-border";
}

function eventLabelClass(auditType: string): string {
  if (auditType.includes("failed") || auditType.includes("rejected")) {
    return "text-red-600 dark:text-red-400";
  }
  if (auditType.includes("completed") || auditType.includes("approved")) {
    return "text-green-600 dark:text-green-400";
  }
  return "text-foreground";
}

function formatDateTime(isoString: string): string {
  const date = new Date(isoString);
  if (Number.isNaN(date.getTime())) return isoString;
  return new Intl.DateTimeFormat("zh-CN", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(date);
}

function formatDay(isoString: string): string {
  const date = new Date(isoString);
  if (Number.isNaN(date.getTime())) return isoString;
  return new Intl.DateTimeFormat("zh-CN", {
    month: "long",
    day: "numeric",
  }).format(date);
}

function isSameDay(a: string, b: string): boolean {
  return new Date(a).toDateString() === new Date(b).toDateString();
}

export function AuditTimeline({ projectId }: AuditTimelineProps) {
  const [events, setEvents] = useState<RunEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    getProjectAuditLogs(projectId)
      .then(({ items }) => {
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

    return () => { cancelled = true; };
  }, [projectId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="size-4 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error) {
    return <p className="text-xs text-destructive">{error}</p>;
  }

  if (events.length === 0) {
    return <p className="py-4 text-center text-xs text-muted-foreground">暂无审计记录</p>;
  }

  return (
    <ol className="relative space-y-0 border-l border-border pl-5">
      {events.map((evt, idx) => {
        const showDayLabel =
          idx === 0 || !isSameDay(evt.created_at, events[idx - 1].created_at);

        return (
          <li key={evt.audit_id} className="relative pb-4 last:pb-0">
            {/* Day separator */}
            {showDayLabel && (
              <div className="mb-3 -ml-5 pl-5 pt-1 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/70">
                {formatDay(evt.created_at)}
              </div>
            )}

            {/* Timeline dot */}
            <span
              className={cn(
                "absolute -left-[21px] top-1 size-2.5 rounded-full border-2 border-background",
                eventDotClass(evt.audit_type),
              )}
            />

            {/* Content */}
            <div className="space-y-0.5">
              <div className="flex items-baseline gap-2">
                <span className={cn("text-[12px] font-medium", eventLabelClass(evt.audit_type))}>
                  {eventLabel(evt.audit_type)}
                </span>
                <span className="text-[10px] text-muted-foreground">
                  {formatDateTime(evt.created_at)}
                </span>
              </div>

              {evt.actor_id && (
                <p className="text-[11px] text-muted-foreground">
                  操作者: <span className="text-foreground/80">{evt.actor_id}</span>
                </p>
              )}
              {evt.decision && (
                <p className="text-[11px] text-muted-foreground">
                  决定: <span className="text-foreground/80">{evt.decision}</span>
                </p>
              )}
              {evt.reason && (
                <p className="text-[11px] text-muted-foreground line-clamp-2">
                  {evt.reason}
                </p>
              )}
              {evt.run_id && (
                <p className="font-mono text-[10px] text-muted-foreground/60">
                  run:{evt.run_id.slice(0, 8)}
                </p>
              )}
            </div>
          </li>
        );
      })}
    </ol>
  );
}
