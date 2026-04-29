import { motion } from "framer-motion";
import { Brain, Lightbulb, Rocket, Sparkles, type LucideIcon } from "lucide-react";

import { cn } from "@/lib/utils";

const QUICK_PROMPT_ITEMS: {
  icon: LucideIcon;
  prompt: string;
}[] = [
  { icon: Rocket, prompt: "帮我整理本周项目进展，输出 3 条重点结论。" },
  { icon: Lightbulb, prompt: "生成一版 CRM MVP 范围说明，控制在一页内。" },
  { icon: Brain, prompt: "把下面的会议讨论改写成正式纪要。" },
  { icon: Sparkles, prompt: "总结当前续费风险，并给出 3 条行动建议。" },
];

interface ChatEmptyStateProps {
  onPromptSelect: (prompt: string) => void;
  isDraft?: boolean;
}

export function ChatEmptyState({ onPromptSelect, isDraft = false }: ChatEmptyStateProps) {
  return (
    <div className="flex flex-1 flex-col px-6 pt-14">
      <div className="mx-auto w-full max-w-[560px]">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
          className="mb-7"
        >
          <div
            className="inline-flex size-10 items-center justify-center rounded-xl border bg-card text-muted-foreground"
            style={{ boxShadow: "var(--shadow-whisper)" }}
          >
            <Sparkles className="size-4" />
          </div>
          <p className="mt-5 text-[11px] tracking-[0.04em] text-muted-foreground">
            {isDraft ? "Exploratory Session" : "New Conversation"}
          </p>
          <h2 className="mt-2 text-[24px] leading-[32px] font-semibold text-foreground">
            {isDraft ? "临时会话" : "新会话"}
          </h2>
          <p className="mt-2 max-w-[440px] text-[14px] leading-[22px] text-muted-foreground">
            {isDraft
              ? "用一个明确任务开始探索。首次发送成功后，系统才会创建正式会话记录。"
              : "选择一个快速开始提示，或直接输入你的问题。"}
          </p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.15, duration: 0.2 }}
          className="mb-3 flex items-center gap-2"
        >
          <p className="text-[12px] font-medium tracking-[0.04em] text-muted-foreground">
            快速开始
          </p>
          <span className="h-px flex-1 bg-border/50" />
        </motion.div>
        <div className="grid gap-2.5 sm:grid-cols-2">
          {QUICK_PROMPT_ITEMS.map(({ icon: Icon, prompt }, i) => (
            <motion.button
              key={prompt}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{
                delay: 0.2 + i * 0.06,
                duration: 0.25,
                ease: [0.16, 1, 0.3, 1],
              }}
              onClick={() => {
                onPromptSelect(prompt);
              }}
              className="group flex items-start gap-3 rounded-lg border bg-card px-4 py-3.5 text-left transition-all duration-200 hover:border-border-strong hover:bg-surface-hover"
            >
              <span
                className={cn(
                  "mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-md border border-black/5 transition-colors",
                  i === 0
                    ? "bg-[var(--accent-soft)] text-[var(--accent)]"
                    : i === 1
                      ? "bg-[var(--status-done-bg)] text-[var(--status-done)]"
                      : i === 2
                        ? "bg-[var(--status-approval-bg)] text-[var(--status-approval)]"
                        : "bg-[var(--surface-hover)] text-foreground",
                )}
              >
                <Icon className="size-4" />
              </span>
              <span className="text-[13px] leading-[20px] text-muted-foreground group-hover:text-foreground">
                {prompt}
              </span>
            </motion.button>
          ))}
        </div>
      </div>
    </div>
  );
}
