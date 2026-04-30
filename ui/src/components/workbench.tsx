import {
  ArrowUpRight,
  Clock3,
  FileSpreadsheet,
  FileText,
  FolderKanban,
  Globe,
  MonitorSmartphone,
  Plus,
  ShieldCheck,
  Sparkles,
  WandSparkles,
} from "lucide-react"

import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

const quickActions = [
  { label: "制作幻灯片", icon: FileText },
  { label: "分析数据", icon: FileSpreadsheet },
  { label: "创建网站", icon: Globe },
  { label: "开发应用", icon: MonitorSmartphone },
]

const starterPrompts = [
  "基于销售周报整理管理层可读的复盘结论",
  "分析一份 CSV，并生成趋势图与摘要",
  "把会议纪要改写为项目执行方案",
  "围绕新项目输出一版可审批的启动文档",
]

const focusCards = [
  {
    title: "当前重点",
    value: "Q2 销售复盘",
    detail: "结果需要补充区域差异与续费风险",
  },
  {
    title: "待推进",
    value: "2 项审批",
    detail: "一个项目摘要、一个交付文档等待确认",
  },
  {
    title: "最近产物",
    value: "7 份输出",
    detail: "报告、方案、纪要和数据分析结果可继续复用",
  },
]

const recentItems = [
  {
    title: "医院经营数据分析报告生成任务",
    meta: "运行中",
    tone: "running",
  },
  {
    title: "基于简历创建浅色个人网站",
    meta: "待确认",
    tone: "approval",
  },
  {
    title: "CSV 文件数据分析及内容分析报告",
    meta: "已完成",
    tone: "done",
  },
] as const

function StatusDot({ tone }: { tone: "running" | "approval" | "done" }) {
  return (
    <span
      className={cn(
        "inline-flex size-2.5 rounded-full",
        tone === "running" && "bg-[var(--status-running)]",
        tone === "approval" && "bg-[var(--status-approval)]",
        tone === "done" && "bg-[var(--status-done)]",
      )}
    />
  )
}

export function Workbench({
  onStartChat,
  onOpenProjects,
  onOpenApprovals,
}: {
  onStartChat: () => void
  onOpenProjects: () => void
  onOpenApprovals: () => void
}) {
  return (
    <div className="min-h-screen bg-background px-4 pb-8 pt-5 md:px-6 md:pt-7">
      <div className="mx-auto grid w-full max-w-[1480px] gap-6 xl:grid-cols-[272px_minmax(0,1fr)_300px]">
        <aside className="hidden xl:flex xl:flex-col">
          <div
            className="flex h-full flex-col rounded-[24px] border border-border/70 bg-[var(--codex-sidebar)] px-4 py-4 backdrop-blur-md"
            style={{ boxShadow: "0 1px 2px rgba(0, 0, 0, 0.04)" }}
          >
            <div className="flex items-center justify-between pb-3">
              <div className="flex items-center gap-3">
                <div className="flex size-10 items-center justify-center rounded-2xl border border-border/80 bg-[rgba(255,255,255,0.88)] text-foreground">
                  <Sparkles className="size-4" />
                </div>
                <div>
                  <p className="text-[13px] font-semibold text-foreground">SwarmMind</p>
                  <p className="text-[11px] tracking-[0.06em] text-muted-foreground">
                    WORK SURFACE
                  </p>
                </div>
              </div>
              <Button
                variant="ghost"
                size="icon-sm"
                className="size-9 rounded-xl"
                onClick={onOpenProjects}
                title="查看项目"
              >
                <FolderKanban className="size-4" />
              </Button>
            </div>

            <Button
              className="mt-4 h-11 justify-start rounded-2xl border border-border/60 bg-[rgba(0,0,0,0.06)] px-4 text-foreground hover:bg-[rgba(0,0,0,0.08)]"
              onClick={onStartChat}
            >
              <Plus className="size-4" />
              新建任务
            </Button>

            <div className="mt-6">
              <p className="px-1 text-[11px] font-semibold tracking-[0.08em] text-muted-foreground">
                最近任务
              </p>
              <div className="mt-3 space-y-2">
                {recentItems.map((item) => (
                  <button
                    key={item.title}
                    type="button"
                    onClick={item.tone === "approval" ? onOpenApprovals : onStartChat}
                    className="w-full rounded-2xl border border-transparent bg-[rgba(255,255,255,0.45)] px-3.5 py-3 text-left transition-colors hover:border-border/60 hover:bg-[rgba(255,255,255,0.72)]"
                  >
                    <div className="flex items-start gap-3">
                      <div className="pt-1">
                        <StatusDot tone={item.tone} />
                      </div>
                      <div className="min-w-0">
                        <p className="line-clamp-2 text-[13px] leading-5 text-foreground">
                          {item.title}
                        </p>
                        <p className="mt-1 text-[11px] tracking-[0.04em] text-muted-foreground">
                          {item.meta}
                        </p>
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            </div>

            <div className="mt-auto rounded-[20px] border border-border/80 bg-[rgba(255,255,255,0.74)] p-4">
              <div className="flex items-start gap-3">
                <div className="flex size-9 items-center justify-center rounded-2xl bg-[var(--accent-soft)] text-[var(--codex-accent)]">
                  <ShieldCheck className="size-4" />
                </div>
                <div>
                  <p className="text-[13px] font-medium text-foreground">可治理执行</p>
                  <p className="mt-1 text-[12px] leading-5 text-muted-foreground">
                    首页保留自由度，但任务进入执行后仍然走审批、追踪和产物沉淀流程。
                  </p>
                </div>
              </div>
            </div>
          </div>
        </aside>

        <section className="flex min-h-[calc(100vh-4rem)] flex-col items-center justify-center xl:-translate-y-8">
          <div className="w-full max-w-[860px]">
            <div className="text-center">
              <p className="text-[13px] tracking-[0.08em] text-muted-foreground">
                SwarmMind 1.6
              </p>
              <h1 className="mx-auto mt-5 max-w-[720px] text-[30px] leading-[1.24] font-semibold tracking-[-0.03em] text-foreground md:text-[42px]">
                先把任务定义清楚，
                <br className="hidden md:block" />
                再稳定地生成结果。
              </h1>
              <p className="mx-auto mt-4 max-w-[560px] text-[14px] leading-7 text-muted-foreground">
                从一个明确任务开始，继续补充附件、约束条件和输出形式，让后续执行更可控。
              </p>
            </div>

            <div
              className="mt-8 rounded-[36px] border border-border/80 bg-[linear-gradient(180deg,rgba(255,255,255,0.98),rgba(246,246,245,0.96))] p-2.5 shadow-[0_18px_48px_rgba(0,0,0,0.06),0_2px_10px_rgba(0,0,0,0.04)] md:p-3"
            >
              <button
                type="button"
                onClick={onStartChat}
                className="flex min-h-[194px] w-full flex-col rounded-[30px] border border-border/80 bg-[rgba(255,255,255,0.98)] px-5 py-5 text-left transition-colors hover:border-border-strong hover:bg-[rgba(255,255,255,1)] md:px-6 md:py-5"
                style={{ boxShadow: "0 8px 24px rgba(0, 0, 0, 0.05)" }}
              >
                <div className="flex items-start justify-between gap-4">
                  <div />
                  <div className="hidden items-center gap-2 rounded-full border border-border/80 bg-secondary/70 px-3 py-1.5 text-[11px] text-muted-foreground md:flex">
                    <Clock3 className="size-3.5" />
                    平均 2-4 分钟产出首版
                  </div>
                </div>

                <div className="mt-3 flex-1">
                  <p className="text-[16px] leading-7 text-muted-foreground/88 md:text-[18px]">
                    分配一个任务或提问任何问题
                  </p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {starterPrompts.map((prompt) => (
                      <span
                        key={prompt}
                        className="inline-flex rounded-full border border-border/80 bg-secondary/65 px-3 py-1.5 text-[12px] text-muted-foreground"
                      >
                        {prompt}
                      </span>
                    ))}
                  </div>
                </div>

                <div className="mt-4 flex items-center justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <span className="inline-flex size-11 items-center justify-center rounded-full border border-border/80 bg-[rgba(255,255,255,0.95)] text-muted-foreground shadow-[0_1px_2px_rgba(0,0,0,0.04)]">
                      <Plus className="size-[18px]" />
                    </span>
                    <span className="inline-flex size-11 items-center justify-center rounded-full border border-border/80 bg-[rgba(255,255,255,0.95)] text-muted-foreground shadow-[0_1px_2px_rgba(0,0,0,0.04)]">
                      <WandSparkles className="size-[18px]" />
                    </span>
                  </div>

                  <span className="inline-flex size-11 items-center justify-center rounded-full bg-[#E5E5E7] text-[#7B7B80]">
                    <ArrowUpRight className="size-[18px]" />
                  </span>
                </div>
              </button>
            </div>

            <div className="mt-5 flex flex-wrap items-center justify-center gap-3">
              {quickActions.map(({ label, icon: Icon }) => (
                <Button
                  key={label}
                  variant="outline"
              className="h-11 rounded-full border-border/80 bg-secondary/65 px-4 text-[13px] hover:bg-secondary/90"
                  onClick={onStartChat}
                >
                  <Icon className="size-4" />
                  {label}
                </Button>
              ))}
              <Button
                variant="ghost"
                className="h-11 rounded-full px-4 text-[13px]"
                onClick={onOpenProjects}
              >
                更多场景
              </Button>
            </div>
          </div>
        </section>

        <aside className="space-y-4">
          {focusCards.map((card) => (
            <div
              key={card.title}
              className="rounded-[24px] border border-border/80 bg-secondary/55 p-5"
            >
              <p className="text-[11px] font-semibold tracking-[0.08em] text-muted-foreground">
                {card.title}
              </p>
              <p className="mt-3 text-[18px] leading-7 font-semibold tracking-[-0.02em] text-foreground">
                {card.value}
              </p>
              <p className="mt-2 text-[12px] leading-6 text-muted-foreground">{card.detail}</p>
            </div>
          ))}

          <div className="rounded-[24px] border border-border/80 bg-[rgba(255,253,251,0.9)] p-5">
            <div className="flex items-start gap-3">
              <div className="flex size-10 items-center justify-center rounded-2xl bg-[var(--accent-soft)] text-[var(--codex-accent)]">
                <ShieldCheck className="size-4" />
              </div>
              <div>
                <p className="text-[15px] font-medium text-foreground">首页改造原则</p>
                <p className="mt-1 text-[12px] leading-6 text-muted-foreground">
                  保持中心任务入口清晰，辅助信息只做轻量提示，不抢主视觉。
                </p>
              </div>
            </div>
          </div>
        </aside>
      </div>
    </div>
  )
}
