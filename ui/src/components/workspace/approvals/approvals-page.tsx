"use client";

import { useEffect, useState } from "react";
import { Loader2, ShieldCheck } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { listApprovals } from "@/core/projects/api";
import type { ApprovalRequest } from "@/core/projects/types";
import { cn } from "@/lib/utils";
import { ApprovalDetail } from "./approval-detail";

type FilterMode = "all" | "pending" | "decided";

function riskBadgeClass(riskTier: string): string {
  switch (riskTier) {
    case "high": return "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400";
    case "medium": return "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400";
    case "low": return "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400";
    default: return "bg-secondary text-muted-foreground";
  }
}

function riskLabel(riskTier: string): string {
  switch (riskTier) {
    case "high": return "高风险";
    case "medium": return "中风险";
    case "low": return "低风险";
    default: return riskTier;
  }
}

function statusBadgeClass(status: string): string {
  switch (status) {
    case "pending": return "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400";
    case "approved": return "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400";
    case "rejected": return "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400";
    default: return "bg-secondary text-muted-foreground";
  }
}

function statusLabel(status: string): string {
  switch (status) {
    case "pending": return "待审批";
    case "approved": return "已批准";
    case "rejected": return "已拒绝";
    default: return status;
  }
}

function relativeTime(isoString: string): string {
  const date = new Date(isoString);
  if (Number.isNaN(date.getTime())) return isoString;
  const now = Date.now();
  const diff = now - date.getTime();
  const minutes = Math.floor(diff / 60000);
  if (minutes < 1) return "刚刚";
  if (minutes < 60) return `${minutes} 分钟前`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} 小时前`;
  const days = Math.floor(hours / 24);
  return `${days} 天前`;
}

export function ApprovalsPage() {
  const [approvals, setApprovals] = useState<ApprovalRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<FilterMode>("all");
  const [selectedApproval, setSelectedApproval] = useState<ApprovalRequest | null>(null);

  const fetchApprovals = () => {
    setLoading(true);
    setError(null);
    listApprovals()
      .then((data) => {
        setApprovals(data.items);
        setLoading(false);
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : "加载失败");
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchApprovals();
    const interval = setInterval(fetchApprovals, 30000);
    return () => { clearInterval(interval); };
  }, []);

  const filteredApprovals = approvals.filter((a) => {
    if (filter === "pending") return a.status === "pending";
    if (filter === "decided") return a.status !== "pending";
    return true;
  });

  return (
    <div className="mx-auto max-w-3xl space-y-6 p-6">
      {/* Title + filter */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <ShieldCheck className="size-5 text-muted-foreground" />
          <h1 className="text-xl font-semibold text-foreground">审批中心</h1>
        </div>
        <div className="flex items-center gap-1">
          {(["all", "pending", "decided"] as FilterMode[]).map((f) => (
            <Button
              key={f}
              variant="ghost"
              size="sm"
              onClick={() => { setFilter(f); }}
              className={cn(
                "rounded-lg text-[13px]",
                filter === f
                  ? "bg-accent text-foreground"
                  : "text-muted-foreground hover:text-foreground",
              )}
            >
              {f === "all" ? "全部" : f === "pending" ? "待审批" : "已决定"}
            </Button>
          ))}
        </div>
      </div>

      {/* Content */}
      {loading ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 className="size-5 animate-spin text-muted-foreground" />
        </div>
      ) : error ? (
        <div className="rounded-xl border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive">
          {error}
        </div>
      ) : filteredApprovals.length === 0 ? (
        <div className="flex flex-col items-center gap-3 py-16 text-muted-foreground">
          <ShieldCheck className="size-10 opacity-30" />
          <p className="text-sm">暂无审批请求</p>
        </div>
      ) : (
        <ul className="space-y-2">
          {filteredApprovals.map((approval) => (
            <li key={approval.approval_id}>
              <button
                type="button"
                onClick={() => { setSelectedApproval(approval); }}
                className={cn(
                  "w-full rounded-xl border border-border bg-card p-4 text-left transition-colors hover:bg-accent/50",
                  selectedApproval?.approval_id === approval.approval_id && "border-accent",
                )}
              >
                <div className="flex flex-wrap items-start gap-2">
                  <span className="flex-1 truncate text-sm font-medium text-foreground">
                    {approval.title}
                  </span>
                  <div className="flex shrink-0 gap-1.5">
                    <Badge className={cn("text-[11px]", riskBadgeClass(approval.risk_tier))}>
                      {riskLabel(approval.risk_tier)}
                    </Badge>
                    <Badge className={cn("text-[11px]", statusBadgeClass(approval.status))}>
                      {statusLabel(approval.status)}
                    </Badge>
                  </div>
                </div>
                <div className="mt-1.5 flex flex-wrap items-center gap-3 text-[11px] text-muted-foreground">
                  {approval.project_id && (
                    <span>项目: {approval.project_id.slice(0, 8)}</span>
                  )}
                  <span>{relativeTime(approval.created_at)}</span>
                </div>
              </button>
            </li>
          ))}
        </ul>
      )}

      {/* Detail panel */}
      {selectedApproval && (
        <ApprovalDetail
          approval={selectedApproval}
          onClose={() => { setSelectedApproval(null); }}
          onDecision={() => {
            fetchApprovals();
            setSelectedApproval(null);
          }}
        />
      )}
    </div>
  );
}
