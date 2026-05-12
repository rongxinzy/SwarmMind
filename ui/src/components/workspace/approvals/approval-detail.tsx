"use client";

import { useState } from "react";
import { Loader2, ShieldCheck, ShieldX, X } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { patchApproval } from "@/core/projects/api";
import type { ApprovalRequest } from "@/core/projects/types";
import { cn } from "@/lib/utils";

interface ApprovalDetailProps {
  approval: ApprovalRequest;
  onClose: () => void;
  onDecision: () => void;
}

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

function statusLabel(status: string): string {
  switch (status) {
    case "pending": return "待审批";
    case "approved": return "已批准";
    case "rejected": return "已拒绝";
    default: return status;
  }
}

function formatTime(isoString: string): string {
  const date = new Date(isoString);
  if (Number.isNaN(date.getTime())) return isoString;
  return new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "numeric",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

export function ApprovalDetail({ approval, onClose, onDecision }: ApprovalDetailProps) {
  const [reason, setReason] = useState("");
  const [approving, setApproving] = useState(false);
  const [rejecting, setRejecting] = useState(false);
  const [decisionError, setDecisionError] = useState<string | null>(null);

  const isPending = approval.status === "pending";
  const isLoading = approving || rejecting;

  const handleDecision = async (decision: "approved" | "rejected") => {
    if (isLoading) return;
    setDecisionError(null);
    if (decision === "approved") setApproving(true);
    else setRejecting(true);
    try {
      await patchApproval(approval.approval_id, {
        status: decision,
        decision_reason: reason.trim() || null,
      });
      onDecision();
    } catch (err) {
      setDecisionError(err instanceof Error ? err.message : "操作失败，请重试");
    } finally {
      setApproving(false);
      setRejecting(false);
    }
  };

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
          <h2 className="text-sm font-semibold text-foreground">审批详情</h2>
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

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
          {/* Title + badges */}
          <div className="space-y-2">
            <h3 className="text-base font-medium text-foreground">{approval.title}</h3>
            <div className="flex flex-wrap gap-1.5">
              <Badge className={cn("text-[11px]", riskBadgeClass(approval.risk_tier))}>
                {riskLabel(approval.risk_tier)}
              </Badge>
              <Badge variant="secondary" className="text-[11px]">
                {statusLabel(approval.status)}
              </Badge>
            </div>
          </div>

          {/* Metadata */}
          <div className="space-y-2 rounded-xl border border-border bg-muted/30 px-3 py-3 text-xs text-muted-foreground">
            {approval.description && (
              <div>
                <span className="font-medium text-foreground">描述</span>
                <p className="mt-0.5 whitespace-pre-wrap">{approval.description}</p>
              </div>
            )}
            {approval.requested_capability && (
              <div>
                <span className="font-medium text-foreground">请求能力</span>
                <p className="mt-0.5 font-mono text-[11px] bg-muted rounded px-1.5 py-0.5 inline-block">
                  {approval.requested_capability}
                </p>
              </div>
            )}
            {approval.run_id && (
              <div>
                <span className="font-medium text-foreground">运行 ID</span>
                <span className="ml-1.5">{approval.run_id.slice(0, 12)}…</span>
              </div>
            )}
            <div>
              <span className="font-medium text-foreground">创建时间</span>
              <span className="ml-1.5">{formatTime(approval.created_at)}</span>
            </div>
          </div>

          {/* Decision area */}
          {isPending ? (
            <div className="space-y-3">
              <Textarea
                value={reason}
                onChange={(e) => { setReason(e.target.value); }}
                placeholder="审批理由（可选）..."
                disabled={isLoading}
                className="min-h-[72px] resize-none text-sm"
              />

              {decisionError && (
                <p className="text-xs text-red-500">{decisionError}</p>
              )}

              <div className="flex gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  className="flex-1 border-red-200 text-red-600 hover:bg-red-50 dark:border-red-800 dark:text-red-400 dark:hover:bg-red-950/30"
                  onClick={() => { void handleDecision("rejected"); }}
                  disabled={isLoading}
                >
                  {rejecting ? (
                    <Loader2 className="size-4 animate-spin" />
                  ) : (
                    <>
                      <ShieldX className="mr-1.5 size-4" />
                      拒绝
                    </>
                  )}
                </Button>
                <Button
                  size="sm"
                  className="flex-1 bg-green-600 text-white hover:bg-green-700 dark:bg-green-700 dark:hover:bg-green-600"
                  onClick={() => { void handleDecision("approved"); }}
                  disabled={isLoading}
                >
                  {approving ? (
                    <Loader2 className="size-4 animate-spin" />
                  ) : (
                    <>
                      <ShieldCheck className="mr-1.5 size-4" />
                      批准
                    </>
                  )}
                </Button>
              </div>
            </div>
          ) : (
            approval.decision_reason && (
              <div className="rounded-xl border border-border bg-muted/30 px-3 py-3 text-xs">
                <span className="font-medium text-foreground">决策理由</span>
                <p className="mt-0.5 text-muted-foreground">{approval.decision_reason}</p>
              </div>
            )
          )}
        </div>
      </div>
    </>
  );
}
