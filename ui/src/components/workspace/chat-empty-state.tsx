import type { ReactNode } from "react";
import { motion } from "framer-motion";
import { Sparkles } from "lucide-react";

export const EMPTY_STATE_PROMPTS = [
  {
    title: "项目周报复盘",
    subtitle: "输出 3 条重点结论",
    prompt: "帮我整理本周项目进展，输出 3 条重点结论。",
    tag: "分析",
    uses: "408 次使用",
    gradient: "linear-gradient(135deg, #18181b 0%, #2b1f58 40%, #0f766e 100%)",
  },
  {
    title: "CRM MVP 范围",
    subtitle: "控制在一页内",
    prompt: "生成一版 CRM MVP 范围说明，控制在一页内。",
    tag: "方案",
    uses: "263 次使用",
    gradient: "linear-gradient(135deg, #f5f1e8 0%, #fbfbfb 65%, #d9f99d 100%)",
  },
  {
    title: "会议纪要改写",
    subtitle: "改写为正式纪要",
    prompt: "把下面的会议讨论改写成正式纪要。",
    tag: "文档",
    uses: "351 次使用",
    gradient: "linear-gradient(135deg, #f3efe7 0%, #f8fafc 55%, #dbeafe 100%)",
  },
  {
    title: "续费风险总结",
    subtitle: "给出 3 条行动建议",
    prompt: "总结当前续费风险，并给出 3 条行动建议。",
    tag: "策略",
    uses: "512 次使用",
    gradient: "linear-gradient(135deg, #0f172a 0%, #111827 45%, #facc15 100%)",
  },
  {
    title: "数据看板摘要",
    subtitle: "生成可读业务结论",
    prompt: "根据这份销售数据看板，提炼 5 条业务结论，并指出两个异常波动。",
    tag: "报表",
    uses: "286 次使用",
    gradient: "linear-gradient(135deg, #e0f2fe 0%, #eff6ff 55%, #dbeafe 100%)",
  },
  {
    title: "产品 PRD 草案",
    subtitle: "整理核心需求结构",
    prompt: "帮我整理一个新功能的 PRD 草案，包含目标、用户场景、关键流程和验收标准。",
    tag: "产品",
    uses: "194 次使用",
    gradient: "linear-gradient(135deg, #fdf2f8 0%, #fff7ed 55%, #fef3c7 100%)",
  },
] as const;

interface ChatEmptyStateProps {
  isDraft?: boolean;
  children?: ReactNode;
}

export function ChatEmptyState({ isDraft = false, children }: ChatEmptyStateProps) {
  return (
    <div className="px-6 pb-14 pt-[9vh]">
      <div className="mx-auto flex w-full max-w-[920px] flex-col items-center text-center">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
          className="w-full"
        >
          <div
            className="inline-flex size-10 items-center justify-center rounded-xl border bg-card text-muted-foreground"
            style={{ boxShadow: "var(--shadow-whisper)" }}
          >
            <Sparkles className="size-4" />
          </div>
          <p className="mt-4 text-[11px] tracking-[0.04em] text-muted-foreground">
            {isDraft ? "Exploratory Session" : "New Conversation"}
          </p>
          <h2 className="mt-3 text-[32px] leading-[1.2] font-semibold text-foreground md:text-[40px]">
            {isDraft ? "我能为你做什么" : "新会话"}
          </h2>
          <p className="mx-auto mt-4 max-w-[620px] text-[15px] leading-8 text-muted-foreground">
            {isDraft
              ? "用一个明确任务开始探索。首次发送成功后，系统才会创建正式会话记录。"
              : "选择一个快速开始提示，或直接输入你的问题。"}
          </p>
        </motion.div>
        {children ? <div className="mt-8 w-full">{children}</div> : null}
      </div>
    </div>
  );
}
