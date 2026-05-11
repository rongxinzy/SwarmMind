"use client";

import { useState } from "react";
import { ShieldAlert, ShieldCheck, ShieldX, Loader2 } from "lucide-react";
import { motion } from "framer-motion";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";

type RiskTier = "low" | "medium" | "high";
type DecisionState = "pending" | "approving" | "rejecting" | "approved" | "rejected";

interface ApprovalCardProps {
  approvalId: string;
  capability: string;
  riskTier: RiskTier;
  runId?: string;
  projectId?: string;
  className?: string;
}

const riskConfig: Record<RiskTier, { label: string; badgeClass: string; borderClass: string }> = {
  low: {
    label: "低风险",
    badgeClass: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
    borderClass: "border-green-200 bg-green-50/50 dark:border-green-800 dark:bg-green-950/20",
  },
  medium: {
    label: "中风险",
    badgeClass: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
    borderClass: "border-amber-200 bg-amber-50/50 dark:border-amber-800 dark:bg-amber-950/20",
  },
  high: {
    label: "高风险",
    badgeClass: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
    borderClass: "border-red-200 bg-red-50/50 dark:border-red-800 dark:bg-red-950/20",
  },
};

async function patchApproval(
  approvalId: string,
  status: "approved" | "rejected",
  reason?: string,
): Promise<void> {
  const res = await fetch(`/api/approvals/${approvalId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status, decision_reason: reason ?? null }),
  });
  if (!res.ok) {
    const err = await res.text().catch(() => "Unknown error");
    throw new Error(`Approval update failed: ${err}`);
  }
}

export function ApprovalCard({
  approvalId,
  capability,
  riskTier,
  className,
}: ApprovalCardProps) {
  const [state, setState] = useState<DecisionState>("pending");
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);

  const config = riskConfig[riskTier] ?? riskConfig.medium;
  const isDecided = state === "approved" || state === "rejected";
  const isLoading = state === "approving" || state === "rejecting";

  const handleDecision = async (decision: "approved" | "rejected") => {
    if (isDecided || isLoading) return;
    setState(decision === "approved" ? "approving" : "rejecting");
    setError(null);
    try {
      await patchApproval(approvalId, decision, reason || undefined);
      setState(decision);
    } catch (err) {
      setError(err instanceof Error ? err.message : "操作失败，请重试");
      setState("pending");
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
      className={cn("w-full", className)}
    >
      <Card className={cn("border", config.borderClass)}>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base font-medium">
            <ShieldAlert className="size-5 text-red-500" />
            <span>需要审批</span>
            <Badge className={cn("ml-auto text-xs", config.badgeClass)}>
              {config.label}
            </Badge>
          </CardTitle>
          <CardDescription className="text-sm text-muted-foreground">
            运行请求执行高风险能力，需要您审批后才能继续
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-4">
          <div className="rounded-md bg-muted/50 px-3 py-2 text-sm font-mono text-foreground">
            {capability}
          </div>

          {!isDecided && (
            <Textarea
              value={reason}
              onChange={(e) => { setReason(e.target.value); }}
              placeholder="审批理由（可选）..."
              disabled={isLoading}
              className="min-h-[56px] resize-none bg-background text-sm"
            />
          )}

          {error && (
            <p className="text-xs text-red-500">{error}</p>
          )}

          {isDecided ? (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex items-center gap-2 text-sm text-muted-foreground"
            >
              {state === "approved" ? (
                <>
                  <ShieldCheck className="size-4 text-green-500" />
                  <span className="text-green-600 dark:text-green-400">已批准</span>
                </>
              ) : (
                <>
                  <ShieldX className="size-4 text-red-500" />
                  <span className="text-red-600 dark:text-red-400">已拒绝</span>
                </>
              )}
            </motion.div>
          ) : (
            <div className="flex gap-2">
              <Button
                size="sm"
                variant="outline"
                className="flex-1 text-red-600 border-red-200 hover:bg-red-50 dark:text-red-400 dark:border-red-800 dark:hover:bg-red-950/30"
                onClick={() => { void handleDecision("rejected"); }}
                disabled={isLoading}
              >
                {state === "rejecting" ? (
                  <Loader2 className="size-4 animate-spin" />
                ) : (
                  <>
                    <ShieldX className="size-4 mr-1.5" />
                    拒绝
                  </>
                )}
              </Button>
              <Button
                size="sm"
                className="flex-1 bg-green-600 hover:bg-green-700 text-white dark:bg-green-700 dark:hover:bg-green-600"
                onClick={() => { void handleDecision("approved"); }}
                disabled={isLoading}
              >
                {state === "approving" ? (
                  <Loader2 className="size-4 animate-spin" />
                ) : (
                  <>
                    <ShieldCheck className="size-4 mr-1.5" />
                    批准
                  </>
                )}
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </motion.div>
  );
}
