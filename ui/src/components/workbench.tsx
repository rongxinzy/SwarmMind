import {
  AlertTriangle,
  Bot,
  CheckCircle2,
  Clock3,
  Compass,
  FileText,
  FolderKanban,
  ShieldCheck,
  Sparkles,
} from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Textarea } from "@/components/ui/textarea"
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

const recentProjects = [
  {
    name: "Enterprise CRM",
    stage: "需求澄清",
    summary: "销售 CRM MVP，等待知识库访问审批",
    tone: "approval" as const,
    label: "待审批",
  },
  {
    name: "Recruiting Automation",
    stage: "方案设计",
    summary: "已形成流程图和面试评分卡草案",
    tone: "running" as const,
    label: "进行中",
  },
  {
    name: "Partner Portal",
    stage: "验收准备",
    summary: "剩余 1 个阻塞，等待 SSO 联调结果",
    tone: "blocked" as const,
    label: "阻塞中",
  },
]

const approvals = [
  {
    title: "Internal KB 访问授权",
    detail: "归属项目：Enterprise CRM",
    eta: "需今天处理",
  },
  {
    title: "GitLab 写权限审批",
    detail: "归属项目：Partner Portal",
    eta: "已等待 5 小时",
  },
]

const runningTeams = [
  {
    name: "软件开发 Team",
    scope: "Enterprise CRM / 需求拆解与技术方案",
    load: "2 个活跃 workstream",
  },
  {
    name: "增长策略 Team",
    scope: "Recruiting Automation / 用户访谈总结",
    load: "1 个活跃 workstream",
  },
]

const focusQueue = [
  {
    title: "把 Enterprise CRM 提升为正式项目",
    detail: "当前需求已超过临时对话范围，下一步应挂载 Team 模板并进入审批闭环。",
    tone: "running" as const,
    label: "建议现在处理",
  },
  {
    title: "收口 GitLab MCP 权限方案",
    detail: "先确认最小权限边界，再决定是否纳入默认项目模板。",
    tone: "approval" as const,
    label: "等待决策",
  },
  {
    title: "整理招聘流程自动化的验收口径",
    detail: "把分散在探索对话里的结论沉淀为项目摘要和产物目录。",
    tone: "draft" as const,
    label: "需要落档",
  },
]

const recentArtifacts = [
  { title: "PRD v0.3", type: "项目产物", tone: "done" as const },
  { title: "风险清单", type: "治理摘要", tone: "blocked" as const },
  { title: "知识库接入建议", type: "调研结论", tone: "chat" as const },
]

function ToneBadge({ children, tone }: { children: React.ReactNode; tone: Tone }) {
  return (
    <Badge variant="outline" className={cn("rounded-full px-2.5", toneClasses[tone])}>
      {children}
    </Badge>
  )
}

function ListRow({
  title,
  subtitle,
  meta,
  tone,
}: {
  title: string
  subtitle: string
  meta: string
  tone?: Tone
}) {
  return (
    <Button variant="ghost" className="h-auto w-full items-start justify-start gap-3 whitespace-normal px-2 py-2 font-normal hover:bg-muted/50">
      <div className="flex min-w-0 flex-1 flex-col gap-1">
        <div className="flex items-center gap-2">
          <span className="truncate text-sm font-medium text-foreground">{title}</span>
          {tone ? <ToneBadge tone={tone}>{meta}</ToneBadge> : null}
        </div>
        <p className="text-xs text-muted-foreground">{subtitle}</p>
      </div>
      {!tone ? <span className="text-xs text-muted-foreground">{meta}</span> : null}
    </Button>
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
  const focusActions = [
    { label: "进入项目空间", onClick: onOpenProjects },
    { label: "查看待审批", onClick: onOpenApprovals },
    { label: "发起新对话", onClick: onStartChat },
  ] as const

  return (
    <div className="min-h-full bg-background">
      <div className="mx-auto flex w-full max-w-[1480px] flex-col gap-4 p-4 md:p-6">
        <section className="grid gap-4 xl:grid-cols-[minmax(0,1.65fr)_minmax(320px,0.95fr)]">
          <Card>
            <CardHeader className="gap-3">
              <div className="flex flex-wrap items-center gap-2">
                <ToneBadge tone="chat">Chat first</ToneBadge>
                <ToneBadge tone="running">3 个项目推进中</ToneBadge>
                <ToneBadge tone="approval">2 个待审批</ToneBadge>
              </div>
              <div className="flex flex-col gap-1">
                <CardTitle className="text-2xl leading-tight md:text-[30px]">
                  今天先推进什么？
                </CardTitle>
                <CardDescription className="max-w-2xl text-sm leading-6">
                  先用临时对话探索问题，再决定是否提升为 Project。正式执行、审批、共享协作都回到项目空间。
                </CardDescription>
              </div>
            </CardHeader>
            <CardContent className="flex flex-col gap-4 pt-5">
              <div className="rounded-lg border bg-background p-3">
                <Textarea
                  readOnly
                  value=""
                  placeholder="输入一句目标，例如：帮我梳理 CRM MVP 的模块边界，并判断现在是否应该立项。"
                  className="min-h-[124px] resize-none border-none bg-transparent px-0 py-0 text-sm shadow-none focus-visible:border-none focus-visible:ring-0"
                />
                <div className="flex flex-wrap items-center gap-2 border-t pt-3">
                  <Button onClick={onStartChat} size="lg" className="gap-2">
                    <Sparkles className="size-4" />
                    新建对话
                  </Button>
                  <Button onClick={onOpenProjects} size="lg" variant="outline" className="gap-2">
                    <FolderKanban className="size-4" />
                    新建项目
                  </Button>
                  <Button onClick={onOpenApprovals} size="lg" variant="ghost" className="gap-2">
                    <ShieldCheck className="size-4" />
                    查看待审批
                  </Button>
                </div>
              </div>

              <div className="grid gap-3 lg:grid-cols-3">
                <div className="rounded-lg border bg-muted/30 p-4">
                  <p className="text-xs font-medium text-muted-foreground">
                    入口原则
                  </p>
                  <p className="mt-2 text-sm font-medium text-foreground">
                    Chat 用于探索，Project 用于执行和治理。
                  </p>
                </div>
                <div className="rounded-lg border bg-muted/30 p-4">
                  <p className="text-xs font-medium text-muted-foreground">
                    Agent Team
                  </p>
                  <p className="mt-2 text-sm font-medium text-foreground">
                    用户看到的是 Team，项目内实际挂载的是 Team 实例。
                  </p>
                </div>
                <div className="rounded-lg border bg-muted/30 p-4">
                  <p className="text-xs font-medium text-muted-foreground">
                    今天建议
                  </p>
                  <p className="mt-2 text-sm font-medium text-foreground">
                    先把 Enterprise CRM 的访问审批清掉，再推进方案拆解。
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <Clock3 className="size-4 text-muted-foreground" />
                今日工作台
              </CardTitle>
              <CardDescription>工作台按权限显示你的运行态、风险和审批堆积。</CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col gap-4 pt-5">
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="rounded-lg border bg-muted/30 p-4">
                  <p className="text-2xl font-semibold tracking-tight">12</p>
                  <p className="mt-1 text-xs text-muted-foreground">活跃项目</p>
                </div>
                <div className="rounded-lg border bg-muted/30 p-4">
                  <p className="text-2xl font-semibold tracking-tight">3</p>
                  <p className="mt-1 text-xs text-muted-foreground">阻塞项目</p>
                </div>
                <div className="rounded-lg border bg-muted/30 p-4">
                  <p className="text-2xl font-semibold tracking-tight">5</p>
                  <p className="mt-1 text-xs text-muted-foreground">待审批</p>
                </div>
                <div className="rounded-lg border bg-muted/30 p-4">
                  <p className="text-2xl font-semibold tracking-tight">4</p>
                  <p className="mt-1 text-xs text-muted-foreground">活跃 Team</p>
                </div>
              </div>

              <div className="rounded-lg border bg-background p-4">
                <div className="flex items-center gap-2">
                  <AlertTriangle className="size-4 text-muted-foreground" />
                  <p className="text-sm font-medium">风险热区</p>
                </div>
                <div className="mt-3 flex flex-col gap-2">
                  <ListRow
                    title="Partner Portal"
                    subtitle="SSO 联调阻塞了验收排期"
                    meta="high risk"
                    tone="blocked"
                  />
                  <ListRow
                    title="Enterprise CRM"
                    subtitle="知识库接入等待企业审批"
                    meta="approval"
                    tone="approval"
                  />
                </div>
              </div>

              <div className="rounded-lg border bg-background p-4">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="size-4 text-muted-foreground" />
                  <p className="text-sm font-medium">推荐下一步</p>
                </div>
                <p className="mt-3 text-sm leading-6 text-muted-foreground">
                  把 CRM 项目从 Chat 摘要提升为正式项目，并挂载软件开发 Team 模板，后续看板、产物和审批才会完整进入治理闭环。
                </p>
              </div>
            </CardContent>
          </Card>
        </section>

        <section className="grid gap-4 xl:grid-cols-3">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <FolderKanban className="size-4 text-muted-foreground" />
                最近项目
              </CardTitle>
              <CardDescription>正式执行、共享协作与审计都归属于 Project。</CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col gap-1 pt-4">
              {recentProjects.map((project) => (
                <ListRow
                  key={project.name}
                  title={project.name}
                  subtitle={`${project.stage} · ${project.summary}`}
                  meta={project.label}
                  tone={project.tone}
                />
              ))}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <ShieldCheck className="size-4 text-muted-foreground" />
                待我审批
              </CardTitle>
              <CardDescription>审批是显式暂停节点，不是默认每轮都出现。</CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col gap-1 pt-4">
              {approvals.map((item) => (
                <ListRow
                  key={item.title}
                  title={item.title}
                  subtitle={item.detail}
                  meta={item.eta}
                />
              ))}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <Bot className="size-4 text-muted-foreground" />
                正在运行的 Agent Team
              </CardTitle>
              <CardDescription>界面保留 Team 语义，项目内由 Team 实例承接正式执行。</CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col gap-1 pt-4">
              {runningTeams.map((team) => (
                <ListRow
                  key={team.name}
                  title={team.name}
                  subtitle={team.scope}
                  meta={team.load}
                />
              ))}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <Compass className="size-4 text-muted-foreground" />
                今日焦点
              </CardTitle>
              <CardDescription>首页负责给方向和动作，历史对话继续留在左侧导航中承接。</CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col gap-3 pt-4">
              {focusQueue.map((item, index) => (
                <div key={item.title} className="rounded-lg border bg-muted/30 p-4">
                  <div className="flex flex-wrap items-center gap-2">
                    <ToneBadge tone={item.tone}>{item.label}</ToneBadge>
                  </div>
                  <p className="mt-3 text-sm font-medium text-foreground">{item.title}</p>
                  <p className="mt-2 text-sm leading-6 text-muted-foreground">{item.detail}</p>
                  <Button variant="outline" size="sm" className="mt-4" onClick={focusActions[index].onClick}>
                    {focusActions[index].label}
                  </Button>
                </div>
              ))}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <FileText className="size-4 text-muted-foreground" />
                最近产物
              </CardTitle>
              <CardDescription>产物、摘要和治理材料要能被追溯，不应埋在聊天流里。</CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col gap-1 pt-4">
              {recentArtifacts.map((artifact) => (
                <ListRow
                  key={artifact.title}
                  title={artifact.title}
                  subtitle={artifact.type}
                  meta={artifact.type}
                  tone={artifact.tone}
                />
              ))}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <Clock3 className="size-4 text-muted-foreground" />
                工作台原则
              </CardTitle>
              <CardDescription>这不是普通聊天壳，而是权限化的执行与治理入口。</CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col gap-3 pt-4">
              <div className="rounded-lg border bg-muted/30 p-4">
                <p className="text-sm font-medium">统一入口</p>
                <p className="mt-2 text-sm leading-6 text-muted-foreground">
                  所有用户先进入工作台，再按权限看到自己的项目、审批、风险和资产。
                </p>
              </div>
              <div className="rounded-lg border bg-muted/30 p-4">
                <p className="text-sm font-medium">范围切换</p>
                <p className="mt-2 text-sm leading-6 text-muted-foreground">
                  结构保持稳定，只切换数据范围，不切成多套页面。
                </p>
              </div>
            </CardContent>
          </Card>
        </section>
      </div>
    </div>
  )
}
