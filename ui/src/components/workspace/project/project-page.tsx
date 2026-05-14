"use client";

import { useEffect, useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  Clock,
  FileText,
  Layers,
  Loader2,
  Play,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { getProjectOverview } from "@/core/projects/api";
import type { ProjectOverviewResponse, Run } from "@/core/projects/types";
import { cn } from "@/lib/utils";
import { ApprovalCard } from "@/components/workspace/messages/approval-card";
import { ProjectComposer } from "./project-composer";
import { ProjectActiveRun } from "./project-active-run";
import { ProjectRunDetail } from "./project-run-detail";
import { TasksPanel } from "./tasks-panel";
import { AuditTimeline } from "./audit-timeline";

interface ProjectPageProps {
  projectId: string;
}

type PageMode = "idle" | "running" | "waiting_approval";

export function ProjectPage({ projectId }: ProjectPageProps) {
  const [overview, setOverview] = useState<ProjectOverviewResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [mode, setMode] = useState<PageMode>("idle");
  const [activePrompt, setActivePrompt] = useState<string>("");
  const [selectedRun, setSelectedRun] = useState<Run | null>(null);
  const [pendingApproval, setPendingApproval] = useState<{
    approvalId: string;
    capability: string;
  } | null>(null);
  const [taskRefreshTick, setTaskRefreshTick] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    getProjectOverview(projectId)
      .then((data) => {
        if (!cancelled) {
          setOverview(data);
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
  }, [projectId]);

  function handleSubmit(content: string) {
    setActivePrompt(content);
    setMode("running");
  }

  function handleTerminal(status: "completed" | "failed") {
    void status;
    setMode("idle");
    setTaskRefreshTick((t) => t + 1);
    getProjectOverview(projectId).then(setOverview).catch(() => {});
  }

  function handleWaitingApproval(approvalId: string, capability: string) {
    setMode("waiting_approval");
    setPendingApproval({ approvalId, capability });
  }

  if (loading) {
    return (
      <div className="flex flex-1 items-center justify-center p-12">
        <Loader2 className="size-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error || !overview) {
    return (
      <div className="flex flex-1 items-center justify-center gap-2 p-12 text-sm text-destructive">
        <AlertCircle className="size-4" />
        {error ?? "项目数据加载失败"}
      </div>
    );
  }

  const { project, stats, recent_artifacts, recent_runs } = overview;

  return (
    <div className="mx-auto max-w-3xl space-y-6 p-6">
      {/* Header */}
      <div className="space-y-1">
        <div className="flex items-start gap-2">
          <h1 className="flex-1 text-xl font-semibold text-foreground">{project.title}</h1>
          <Badge variant="secondary" className="shrink-0 text-[11px]">
            {project.status}
          </Badge>
        </div>
        {project.phase && (
          <p className="text-xs text-muted-foreground">阶段: {project.phase}</p>
        )}
        {project.source_conversation_id && (
          <p className="text-xs text-muted-foreground">
            来源对话:{" "}
            <a
              href={`/?conversation=${project.source_conversation_id}`}
              className="underline-offset-2 hover:underline"
            >
              {project.source_conversation_id.slice(0, 8)}…
            </a>
          </p>
        )}
      </div>

      {/* Goal */}
      {project.goal && (
        <Section title="目标">
          <p className="whitespace-pre-wrap text-sm text-foreground/90">{project.goal}</p>
        </Section>
      )}

      {/* Next step */}
      {project.next_step && (
        <Section title="下一步">
          <p className="whitespace-pre-wrap text-sm text-foreground/90">{project.next_step}</p>
        </Section>
      )}

      {/* Stats strip */}
      <div className="grid grid-cols-4 gap-3">
        <StatCard icon={<Layers className="size-3.5" />} label="任务" value={stats.task_count} />
        <StatCard icon={<FileText className="size-3.5" />} label="产物" value={stats.artifact_count} />
        <StatCard icon={<Play className="size-3.5" />} label="运行" value={stats.run_count} />
        <StatCard
          icon={<AlertCircle className="size-3.5" />}
          label="待审批"
          value={stats.pending_approval_count}
          highlight={stats.pending_approval_count > 0}
        />
      </div>

      {/* Composer */}
      <ProjectComposer
        disabled={mode !== "idle"}
        onSubmit={handleSubmit}
      />

      {/* Active run panel */}
      {mode === "running" && (
        <ProjectActiveRun
          projectId={projectId}
          prompt={activePrompt}
          onTerminal={handleTerminal}
          onWaitingApproval={handleWaitingApproval}
        />
      )}

      {/* Waiting for approval */}
      {mode === "waiting_approval" && pendingApproval && (
        <ApprovalCard
          approvalId={pendingApproval.approvalId}
          capability={pendingApproval.capability}
          riskTier="high"
        />
      )}

      {/* Task Kanban */}
      <Section title="任务看板">
        <TasksPanel projectId={projectId} refreshTick={taskRefreshTick} />
      </Section>

      {/* Recent runs */}
      {recent_runs.length > 0 && (
        <Section title="近期执行">
          <ul className="space-y-1.5">
            {recent_runs.map((run) => (
              <li
                key={run.run_id}
                className="flex cursor-pointer items-center gap-2 rounded-md px-1 py-0.5 text-sm transition-colors hover:bg-muted/60"
                onClick={() => { setSelectedRun(run); }}
              >
                <StatusDot status={run.status} />
                <span className="flex-1 truncate text-muted-foreground">
                  {run.goal ?? run.run_id.slice(0, 8)}
                </span>
                <span className="shrink-0 text-[11px] text-muted-foreground">{run.status}</span>
              </li>
            ))}
          </ul>
        </Section>
      )}

      {/* Recent artifacts */}
      {recent_artifacts.length > 0 && (
        <Section title="近期产物">
          <ul className="space-y-1.5">
            {recent_artifacts.map((art) => (
              <li key={art.artifact_id} className="flex items-center gap-2 text-sm">
                <FileText className="size-3.5 shrink-0 text-muted-foreground" />
                <span className="flex-1 truncate">{art.name ?? art.artifact_id.slice(0, 8)}</span>
                {art.artifact_type && (
                  <Badge variant="secondary" className="shrink-0 text-[10px]">
                    {art.artifact_type}
                  </Badge>
                )}
              </li>
            ))}
          </ul>
        </Section>
      )}

      {/* Audit timeline */}
      <Section title="审计时间线">
        <AuditTimeline projectId={projectId} />
      </Section>

      {/* Run detail drawer */}
      {selectedRun && (
        <ProjectRunDetail
          projectId={projectId}
          run={selectedRun}
          onClose={() => { setSelectedRun(null); }}
        />
      )}
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="space-y-2 rounded-xl border border-border bg-card p-4">
      <h2 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">{title}</h2>
      {children}
    </div>
  );
}

function StatCard({
  icon,
  label,
  value,
  highlight = false,
}: {
  icon: React.ReactNode;
  label: string;
  value: number;
  highlight?: boolean;
}) {
  return (
    <div
      className={cn(
        "flex flex-col gap-1 rounded-xl border p-3",
        highlight ? "border-amber-200 bg-amber-50 dark:border-amber-800 dark:bg-amber-950/30" : "border-border bg-card",
      )}
    >
      <span className={cn("text-muted-foreground", highlight && "text-amber-600 dark:text-amber-400")}>{icon}</span>
      <span className="text-xl font-semibold text-foreground">{value}</span>
      <span className="text-[11px] text-muted-foreground">{label}</span>
    </div>
  );
}

function StatusDot({ status }: { status: string }) {
  const color =
    status === "completed" || status === "done"
      ? "text-green-500"
      : status === "blocked" || status === "failed"
        ? "text-red-500"
        : status === "in_progress" || status === "running"
          ? "text-blue-500"
          : "text-muted-foreground";

  const Icon = status === "completed" || status === "done" ? CheckCircle2 : Clock;
  return <Icon className={cn("size-3.5 shrink-0", color)} />;
}
