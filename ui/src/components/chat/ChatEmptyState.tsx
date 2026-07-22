import type { LucideIcon } from "lucide-react"
import { BarChart3, FileText, Presentation, Search, SquareChartGantt, WandSparkles } from "lucide-react"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

interface ChatEmptyStateProps {
  onSuggestion?: (suggestion: string) => void
}

const SHORTCUTS: {
  label: string
  prompt: string
  icon: LucideIcon
  primary?: boolean
}[] = [
  {
    label: "项目简报",
    prompt: "把这个想法整理成一页项目简报，包含目标、范围、风险和下一步。",
    icon: FileText,
    primary: true,
  },
  {
    label: "执行计划",
    prompt: "把这个任务拆成可执行计划，给出里程碑、依赖、风险和第一步交付。",
    icon: SquareChartGantt,
  },
  {
    label: "市场调研",
    prompt: "围绕这个主题做一轮调研，输出关键发现、证据来源和建议行动。",
    icon: Search,
  },
  {
    label: "演示大纲",
    prompt: "把这些材料整理成一份面向团队讨论的幻灯片大纲。",
    icon: Presentation,
  },
  {
    label: "数据报告",
    prompt: "分析这组数据，找出趋势、异常、解释和下一步建议。",
    icon: BarChart3,
  },
  {
    label: "交付物改写",
    prompt: "把现有内容改写成更清晰、更适合交付的版本，并列出修改依据。",
    icon: WandSparkles,
  },
]

export function ChatEmptyState({ onSuggestion }: ChatEmptyStateProps) {
  return (
    <section className="flex w-full flex-col items-center text-center">
      <h1 className="max-w-[820px] text-[42px] font-normal leading-[1.07] tracking-normal text-[#101010] sm:text-[56px]">
        开始一个
        <br />
        新任务
      </h1>

      {onSuggestion && (
        <div className="mt-10 flex w-full max-w-[820px] flex-wrap justify-center gap-2.5">
          {SHORTCUTS.map((shortcut) => (
            <Button
              key={shortcut.label}
              type="button"
              variant="outline"
              className={cn(
                "h-12 min-w-[136px] justify-start rounded-full border px-4 text-left text-[14px] font-normal shadow-[0_1px_2px_rgba(0,0,0,0.03)] transition-colors",
                shortcut.primary
                  ? "border-[#101010] bg-[#101010] text-white shadow-[0_8px_24px_rgba(0,0,0,0.13)] hover:bg-[#242424]"
                  : "border-[#e7e7e4] bg-white text-[#565653] hover:border-[#d7d7d2] hover:bg-[#f8f8f6] hover:text-[#1f1f1d]",
              )}
              onClick={() => onSuggestion(shortcut.prompt)}
            >
              <shortcut.icon
                className={cn(
                  "size-4 shrink-0",
                  shortcut.primary ? "text-white" : "text-[#7d7d79]",
                )}
              />
              <span className="truncate">{shortcut.label}</span>
            </Button>
          ))}
        </div>
      )}
    </section>
  )
}
