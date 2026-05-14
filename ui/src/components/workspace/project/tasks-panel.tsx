"use client";

import { useEffect, useState } from "react";
import { CheckCircle2, Circle, Clock, Loader2, OctagonX } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { getProjectTasks } from "@/core/projects/api";
import type { Task } from "@/core/projects/types";
import { cn } from "@/lib/utils";

interface TasksPanelProps {
  projectId: string;
  /** When true the panel refetches tasks (e.g. after a run completes). */
  refreshTick?: number;
}

type KanbanColumn = {
  key: string;
  label: string;
  statuses: string[];
  icon: React.ReactNode;
  className: string;
};

const COLUMNS: KanbanColumn[] = [
  {
    key: "todo",
    label: "待办",
    statuses: ["todo", "pending", "created"],
    icon: <Circle className="size-3.5 text-muted-foreground" />,
    className: "border-border bg-muted/30",
  },
  {
    key: "in_progress",
    label: "进行中",
    statuses: ["in_progress", "running"],
    icon: <Clock className="size-3.5 text-blue-500" />,
    className: "border-blue-200 bg-blue-50/40 dark:border-blue-800 dark:bg-blue-950/20",
  },
  {
    key: "blocked",
    label: "阻塞",
    statuses: ["blocked", "awaiting_approval"],
    icon: <OctagonX className="size-3.5 text-amber-500" />,
    className: "border-amber-200 bg-amber-50/40 dark:border-amber-800 dark:bg-amber-950/20",
  },
  {
    key: "done",
    label: "完成",
    statuses: ["done", "completed", "failed"],
    icon: <CheckCircle2 className="size-3.5 text-green-500" />,
    className: "border-green-200 bg-green-50/40 dark:border-green-800 dark:bg-green-950/20",
  },
];

function priorityBadgeClass(priority: string): string {
  switch (priority) {
    case "high": return "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400";
    case "medium": return "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400";
    default: return "bg-secondary text-muted-foreground";
  }
}

function TaskCard({ task }: { task: Task }) {
  return (
    <div className="rounded-lg border border-border bg-card p-2.5 shadow-sm space-y-1.5">
      <p className="text-[12px] font-medium leading-5 text-foreground line-clamp-2">{task.title}</p>
      <div className="flex flex-wrap items-center gap-1.5">
        {task.priority && task.priority !== "low" && (
          <Badge className={cn("text-[10px] px-1.5 py-0", priorityBadgeClass(task.priority))}>
            {task.priority === "high" ? "高" : "中"}
          </Badge>
        )}
        {task.run_id && (
          <span className="text-[10px] text-muted-foreground font-mono">
            {task.run_id.slice(0, 6)}
          </span>
        )}
      </div>
    </div>
  );
}

export function TasksPanel({ projectId, refreshTick = 0 }: TasksPanelProps) {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    getProjectTasks(projectId)
      .then(({ items }) => {
        if (!cancelled) {
          setTasks(items);
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
  }, [projectId, refreshTick]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="size-4 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error) {
    return (
      <p className="text-xs text-destructive">{error}</p>
    );
  }

  const columns = COLUMNS.map((col) => ({
    ...col,
    tasks: tasks.filter((t) => col.statuses.includes(t.status)),
  }));

  const totalTasks = tasks.length;

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-[11px] text-muted-foreground">{totalTasks} 个任务</span>
      </div>

      {totalTasks === 0 ? (
        <p className="py-4 text-center text-xs text-muted-foreground">暂无任务</p>
      ) : (
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          {columns.map((col) => (
            <div
              key={col.key}
              className={cn("rounded-xl border p-2 space-y-2 min-h-[80px]", col.className)}
            >
              <div className="flex items-center gap-1.5">
                {col.icon}
                <span className="text-[11px] font-semibold text-foreground">{col.label}</span>
                <span className="ml-auto text-[10px] text-muted-foreground">{col.tasks.length}</span>
              </div>
              <div className="space-y-1.5">
                {col.tasks.map((task) => (
                  <TaskCard key={task.task_id} task={task} />
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
