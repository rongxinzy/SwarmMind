import {
  CheckCircle2,
  Copy,
  Download,
  FileSpreadsheet,
  FileText,
  FolderKanban,
  ListChecks,
  PencilLine,
  RotateCcw,
  ShieldCheck,
  Sparkles,
  WandSparkles,
} from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { cn } from "@/lib/utils"

type Tone = "running" | "approval" | "blocked" | "done" | "chat" | "draft"

const toneClasses: Record<Tone, string> = {
  running: "status-pill-running",
  approval: "status-pill-approval",
  blocked: "status-pill-blocked",
  done: "status-pill-done",
  chat: "status-pill-chat",
  draft: "status-pill-draft",
}

const functionCards = [
  {
    title: "文档生成",
    description: "一键生成结构化报告、方案与会议纪要。",
    icon: <FileText className="size-5" />,
    tone: "var(--accent-soft)",
  },
  {
    title: "数据分析",
    description: "上传数据后输出洞察、结论和汇报摘要。",
    icon: <FileSpreadsheet className="size-5" />,
    tone: "var(--status-done-bg)",
  },
  {
    title: "任务拆解",
    description: "把目标拆成步骤、负责人和交付清单。",
    icon: <ListChecks className="size-5" />,
    tone: "var(--status-approval-bg)",
  },
  {
    title: "知识问答",
    description: "基于企业知识源生成可引用的回答。",
    icon: <Sparkles className="size-5" />,
    tone: "var(--surface-hover)",
  },
]

const steps = [
  { step: "Step 1", title: "输入信息", detail: "填写主题、风格、受众等核心字段。" },
  { step: "Step 2", title: "AI 处理", detail: "系统生成结构化草稿并给出处理状态。" },
  { step: "Step 3", title: "输出结果", detail: "结果以标题、段落和列表形式展示。" },
  { step: "Step 4", title: "编辑 / 导出", detail: "支持局部修改、复制、导出和复用。" },
]

const recentTasks = [
  {
    title: "Q2 销售复盘报告",
    detail: "销售团队 / 需要补充区域维度分析",
    tone: "running" as const,
    meta: "生成中",
  },
  {
    title: "Partner Portal 项目摘要",
    detail: "产品团队 / 等待 SSO 结论后重新输出",
    tone: "approval" as const,
    meta: "待确认",
  },
  {
    title: "招聘流程自动化方案",
    detail: "HR 团队 / 已导出 docx 版本",
    tone: "done" as const,
    meta: "已完成",
  },
]

const recentHistory = [
  "CRM MVP 范围定义",
  "企业知识接入建议",
  "销售周报模板 v2",
]

function ToneBadge({ children, tone }: { children: React.ReactNode; tone: Tone }) {
  return (
    <Badge variant="outline" className={cn("px-2.5 py-0.5", toneClasses[tone])}>
      {children}
    </Badge>
  )
}

function SectionTitle({
  icon,
  title,
  description,
}: {
  icon: React.ReactNode
  title: string
  description: string
}) {
  return (
    <div className="flex items-start gap-3">
      <div className="mt-0.5 flex size-8 items-center justify-center rounded-md border border-border bg-secondary text-foreground">
        {icon}
      </div>
      <div>
        <h2 className="text-[18px] leading-7 font-semibold tracking-[-0.01em] text-foreground">{title}</h2>
        <p className="mt-1 text-[14px] leading-[22px] text-muted-foreground">{description}</p>
      </div>
    </div>
  )
}

function FunctionCard({
  icon,
  title,
  description,
  tone,
}: {
  icon: React.ReactNode
  title: string
  description: string
  tone: string
}) {
  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <div className="flex items-start gap-3">
        <div
          className="flex size-9 shrink-0 items-center justify-center rounded-md border border-black/5"
          style={{ backgroundColor: tone }}
        >
          {icon}
        </div>
        <div className="min-w-0">
          <h3 className="text-[15px] leading-6 font-semibold tracking-[-0.01em] text-foreground">{title}</h3>
          <p className="mt-1 text-[13px] leading-[20px] text-muted-foreground">{description}</p>
        </div>
      </div>
    </div>
  )
}

function StepCard({
  step,
  title,
  detail,
}: {
  step: string
  title: string
  detail: string
}) {
  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <p className="text-[11px] leading-4 tracking-[0.08em] text-muted-foreground">{step}</p>
      <h3 className="mt-2 text-[15px] leading-6 font-semibold tracking-[-0.01em] text-foreground">{title}</h3>
      <p className="mt-1.5 text-[13px] leading-[20px] text-muted-foreground">{detail}</p>
    </div>
  )
}

function ResultAction({ icon, label }: { icon: React.ReactNode; label: string }) {
  return (
    <Button variant="outline" size="sm" className="h-8 rounded-md px-2.5 text-[12px]">
      {icon}
      {label}
    </Button>
  )
}

function ListRow({
  title,
  detail,
  meta,
  tone,
}: {
  title: string
  detail: string
  meta: string
  tone: Tone
}) {
  return (
    <div className="rounded-lg border border-border bg-card px-4 py-3.5">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-[14px] leading-[22px] font-medium tracking-[-0.01em] text-foreground">{title}</p>
          <p className="mt-0.5 text-[12px] leading-[18px] text-muted-foreground">{detail}</p>
        </div>
        <ToneBadge tone={tone}>{meta}</ToneBadge>
      </div>
    </div>
  )
}

function OutputListItem({ children }: { children: React.ReactNode }) {
  return (
    <li className="text-[14px] leading-[22px] text-muted-foreground">{children}</li>
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
    <div className="px-4 pb-6 pt-4 md:px-6 md:pb-8">
      <div className="mx-auto flex w-full max-w-[1440px] flex-col gap-5">
        <section className="rounded-lg border border-border bg-secondary/65 p-6">
          <div className="grid gap-8 xl:grid-cols-[minmax(0,1.15fr)_320px] xl:items-start">
            <div>
              <p className="text-[11px] leading-4 tracking-[0.04em] text-muted-foreground">Enterprise AI Workspace</p>
              <h1 className="mt-3 text-[24px] leading-8 font-semibold text-foreground">
                强结构、强引导、强结果
              </h1>
              <p className="mt-3 max-w-[620px] text-[14px] leading-[22px] text-muted-foreground">
                首页不再鼓励自由发散，而是直接进入结构化生成流程，让用户更快得到可编辑、可导出、可复用的结果。
              </p>
              <div className="mt-5 flex flex-wrap gap-2">
                <Button onClick={onStartChat}>开始生成</Button>
                <Button variant="outline" onClick={onOpenProjects}>
                  保存为项目
                </Button>
              </div>
            </div>

            <div className="rounded-lg border border-border bg-card p-4">
              <p className="text-[10px] leading-4 tracking-[0.1em] text-muted-foreground uppercase">工作流摘要</p>
              <div className="mt-4 space-y-3">
                <div className="flex items-center justify-between gap-4 text-[14px] leading-[22px]">
                  <span className="text-muted-foreground">当前重点</span>
                  <span className="font-medium text-foreground">销售复盘报告</span>
                </div>
                <div className="flex items-center justify-between gap-4 text-[14px] leading-[22px]">
                  <span className="text-muted-foreground">待审批</span>
                  <span className="font-medium text-foreground">2 项</span>
                </div>
                <div className="flex items-center justify-between gap-4 text-[14px] leading-[22px]">
                  <span className="text-muted-foreground">可导出结果</span>
                  <span className="font-medium text-foreground">7 份</span>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="grid gap-5 xl:grid-cols-[minmax(0,1.45fr)_320px]">
          <div className="space-y-5">
            <Card>
              <CardHeader>
                <SectionTitle
                  icon={<WandSparkles className="size-4" />}
                  title="结构化输入"
                  description="用表单收集关键信息，再由 AI 处理，不再只给一个大输入框。"
                />
              </CardHeader>
              <CardContent className="space-y-5">
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="space-y-2">
                    <label className="field-label">主题</label>
                    <Input value="Q2 销售复盘报告" readOnly />
                  </div>
                  <div className="space-y-2">
                    <label className="field-label">风格</label>
                    <Input value="正式 / 管理层汇报" readOnly />
                  </div>
                  <div className="space-y-2">
                    <label className="field-label">受众</label>
                    <Input value="销售负责人 / 管理层" readOnly />
                  </div>
                  <div className="space-y-2">
                    <label className="field-label">输出格式</label>
                    <Input value="报告 + 关键结论 + 行动建议" readOnly />
                  </div>
                </div>

                <div className="rounded-lg border border-border bg-secondary/80 p-4">
                  <p className="field-label">补充说明</p>
                  <ul className="mt-3 list-disc space-y-1 pl-5">
                    <OutputListItem>强调北区和华东区的增长差异</OutputListItem>
                    <OutputListItem>补充续费风险与渠道贡献两个章节</OutputListItem>
                    <OutputListItem>输出结果需要支持 docx 与 PDF 导出</OutputListItem>
                  </ul>
                </div>

                <div className="flex flex-wrap gap-2 pt-1">
                  <Button onClick={onStartChat}>开始生成</Button>
                  <Button variant="outline" onClick={onOpenProjects}>
                    保存为项目
                  </Button>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <SectionTitle
                  icon={<ListChecks className="size-4" />}
                  title="标准流程"
                  description="统一的 4 步流程，减少学习成本。"
                />
              </CardHeader>
              <CardContent className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                {steps.map((step) => (
                  <StepCard key={step.step} step={step.step} title={step.title} detail={step.detail} />
                ))}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <SectionTitle
                  icon={<FileText className="size-4" />}
                  title="输出结果预览"
                  description="结果以可读、可编辑、可导出的结构展示。"
                />
              </CardHeader>
              <CardContent className="space-y-5">
                <div className="rounded-lg border border-border bg-secondary/80 p-4">
                  <div className="flex flex-wrap items-center gap-2">
                    <ToneBadge tone="running">Generating</ToneBadge>
                    <span className="text-[12px] leading-[18px] text-muted-foreground">结果正在补充区域分析章节</span>
                  </div>
                  <div className="mt-3 grid gap-2">
                    <div className="skeleton-line h-4 rounded-sm" />
                    <div className="skeleton-line h-4 rounded-sm w-[82%]" />
                    <div className="skeleton-line h-4 rounded-sm w-[64%]" />
                  </div>
                </div>

                <div className="rounded-lg border border-border bg-card px-4 py-3.5 fade-up">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <h3 className="text-[15px] leading-6 font-semibold tracking-[-0.01em] text-foreground">Q2 销售复盘报告</h3>
                      <p className="mt-0.5 text-[12px] leading-[18px] text-muted-foreground">
                        结构化输出，已自动生成摘要、列表与关键结论。
                      </p>
                    </div>
                    <ToneBadge tone="done">Success</ToneBadge>
                  </div>

                  <div className="mt-4 space-y-3.5">
                    <div>
                      <p className="text-[14px] leading-[22px] font-medium text-foreground">执行摘要</p>
                      <p className="mt-2 text-[14px] leading-[22px] text-muted-foreground">
                        Q2 总体收入保持增长，但区域波动明显，北区续费风险上升，华东区由渠道带动的新增表现最好。
                      </p>
                    </div>

                    <div>
                      <p className="text-[14px] leading-[22px] font-medium text-foreground">关键结论</p>
                      <ul className="mt-2 list-disc space-y-1 pl-5">
                        <OutputListItem>北区续费风险主要集中在大客户延期采购。</OutputListItem>
                        <OutputListItem>渠道贡献提升明显，建议保留联合营销预算。</OutputListItem>
                        <OutputListItem>重点项目需要单独跟踪合同推进状态。</OutputListItem>
                      </ul>
                    </div>
                  </div>
                </div>

                <div className="flex flex-wrap gap-2 pt-1">
                  <ResultAction icon={<PencilLine className="size-4" />} label="编辑" />
                  <ResultAction icon={<Copy className="size-4" />} label="复制" />
                  <ResultAction icon={<Download className="size-4" />} label="导出 PDF / docx" />
                  <ResultAction icon={<RotateCcw className="size-4" />} label="重新生成" />
                </div>
              </CardContent>
            </Card>
          </div>

          <div className="space-y-5">
            <Card>
              <CardHeader>
                <SectionTitle
                  icon={<Sparkles className="size-4" />}
                  title="功能入口"
                  description="用户第一眼就知道能做什么。"
                />
              </CardHeader>
              <CardContent className="grid gap-3 sm:grid-cols-2 xl:grid-cols-1">
                {functionCards.map((card) => (
                  <FunctionCard
                    key={card.title}
                    icon={card.icon}
                    title={card.title}
                    description={card.description}
                    tone={card.tone}
                  />
                ))}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <SectionTitle
                  icon={<ShieldCheck className="size-4" />}
                  title="最近任务"
                  description="聚焦需要继续推进的结构化结果。"
                />
              </CardHeader>
              <CardContent className="space-y-2.5">
                {recentTasks.map((item) => (
                  <ListRow
                    key={item.title}
                    title={item.title}
                    detail={item.detail}
                    meta={item.meta}
                    tone={item.tone}
                  />
                ))}
                <Button variant="outline" onClick={onOpenApprovals} className="w-full">
                  查看全部审批
                </Button>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <SectionTitle
                  icon={<FolderKanban className="size-4" />}
                  title="历史记录"
                  description="最近使用过的任务主题与结果上下文。"
                />
              </CardHeader>
              <CardContent className="space-y-1.5">
                {recentHistory.map((item) => (
                  <div key={item} className="rounded-lg border border-border bg-card px-4 py-2.5">
                    <p className="text-[14px] leading-[22px] text-foreground">{item}</p>
                  </div>
                ))}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <SectionTitle
                  icon={<CheckCircle2 className="size-4" />}
                  title="可控性"
                  description="让用户始终感觉自己在控制 AI。"
                />
              </CardHeader>
              <CardContent className="space-y-1.5">
                <div className="rounded-lg border border-border bg-secondary/80 p-4">
                  <p className="field-label">提供能力</p>
                  <ul className="mt-2 list-disc space-y-1 pl-5">
                    <OutputListItem>修改输入后重新生成</OutputListItem>
                    <OutputListItem>对某一段落做局部重写</OutputListItem>
                    <OutputListItem>将当前结果保存为模板复用</OutputListItem>
                  </ul>
                </div>
              </CardContent>
            </Card>
          </div>
        </section>
      </div>
    </div>
  )
}
