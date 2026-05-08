"use client";

import { useState } from "react";
import { ChevronDown, ChevronRight, Loader2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { getMessageTrace, type TraceSummaryResponse } from "@/core/trace/api";
import { cn } from "@/lib/utils";

interface TraceSummaryProps {
  conversationId: string;
  messageId: string;
}

export function TraceSummary({ conversationId, messageId }: TraceSummaryProps) {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<TraceSummaryResponse | null>(null);
  const [error, setError] = useState(false);

  const handleToggle = () => {
    if (!open && !data && !loading) {
      setLoading(true);
      setError(false);
      getMessageTrace(conversationId, messageId)
        .then((result) => {
          setData(result);
          setLoading(false);
        })
        .catch(() => {
          setError(true);
          setLoading(false);
        });
    }
    setOpen((prev) => !prev);
  };

  return (
    <div className="mt-2 rounded-lg border border-border/60 bg-surface-hover/40 text-xs">
      <button
        type="button"
        onClick={handleToggle}
        className="flex w-full items-center gap-1.5 px-3 py-2 text-left text-muted-foreground transition-colors hover:text-foreground"
      >
        {loading ? (
          <Loader2 className="size-3 animate-spin" />
        ) : open ? (
          <ChevronDown className="size-3" />
        ) : (
          <ChevronRight className="size-3" />
        )}
        <span className="font-medium">执行摘要</span>
        {data && !open && (
          <span className="ml-auto text-[10px] opacity-60">
            {data.steps_count} 步 · {data.subagent_calls_count} 子任务
          </span>
        )}
      </button>

      {open && (
        <div className="border-t border-border/40 px-3 pb-3 pt-2">
          {loading && (
            <div className="flex items-center gap-1.5 text-muted-foreground">
              <Loader2 className="size-3 animate-spin" />
              <span>加载中…</span>
            </div>
          )}
          {error && !loading && (
            <p className="text-muted-foreground">摘要暂不可用</p>
          )}
          {data && !loading && (
            <div className="space-y-2">
              {data.summary && (
                <p className="text-foreground/90">{data.summary}</p>
              )}
              <div className="flex flex-wrap gap-1.5">
                <CountBadge label="步骤" value={data.steps_count} />
                <CountBadge label="子任务" value={data.subagent_calls_count} />
                <CountBadge label="产物" value={data.artifacts_count} />
                {data.blocked_points.map((pt, i) => (
                  <Badge
                    key={i}
                    variant="secondary"
                    className={cn("text-[10px]", "border-amber-300 bg-amber-50 text-amber-700 dark:border-amber-700 dark:bg-amber-950/40 dark:text-amber-400")}
                  >
                    阻塞: {pt}
                  </Badge>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function CountBadge({ label, value }: { label: string; value: number }) {
  return (
    <Badge variant="secondary" className="text-[10px]">
      {label} {value}
    </Badge>
  );
}
