"use client";

import { useRef, useState } from "react";
import type { KeyboardEvent } from "react";
import { Loader2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";

interface ProjectComposerProps {
  disabled?: boolean;
  onSubmit: (content: string) => void;
}

export function ProjectComposer({ disabled = false, onSubmit }: ProjectComposerProps) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSubmit = () => {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSubmit(trimmed);
    setValue("");
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="space-y-2 rounded-xl border border-border bg-card p-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          发起执行
        </h2>
        {disabled && (
          <Badge
            variant="secondary"
            className={cn(
              "text-[11px]",
              "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
            )}
          >
            运行中...
          </Badge>
        )}
      </div>

      <Textarea
        ref={textareaRef}
        value={value}
        onChange={(e) => { setValue(e.target.value); }}
        onKeyDown={handleKeyDown}
        placeholder="输入执行指令，按 Cmd+Enter 或点击执行按钮提交..."
        disabled={disabled}
        className="min-h-[80px] resize-none text-sm"
      />

      <div className="flex items-center justify-between">
        <span className="text-[11px] text-muted-foreground">Cmd/Ctrl + Enter 提交</span>
        {disabled ? (
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <Loader2 className="size-3.5 animate-spin" />
            <span>执行中...</span>
          </div>
        ) : (
          <Button
            size="sm"
            onClick={handleSubmit}
            disabled={!value.trim()}
          >
            执行
          </Button>
        )}
      </div>
    </div>
  );
}
