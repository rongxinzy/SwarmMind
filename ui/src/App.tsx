import { useState, type ReactNode } from "react"
import {
  Bot,
  BookOpenText,
  Clock3,
  FolderKanban,
  History,
  Library,
  Search,
  Sparkles,
} from "lucide-react"

import { Workbench } from "@/components/workbench"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Sidebar, SidebarView, VIEW_LABELS } from "@/components/ui/sidebar"
import { V0Chat } from "@/components/ui/v0-ai-chat"

const viewDescriptions: Record<SidebarView, string> = {
  workbench: "每个用户的首页工作台，聚合项目、审批、风险和资产。",
  chat: "临时 Chat 是一等入口，用于探索、提问和快速验证。",
  teams: "用户看到的是 Agent Team；治理页维护的是可复用配置模板。",
  skills: "统一管理 MCP、Skills 和它们对 Team / Project 的绑定关系。",
  assets: "沉淀正式产物、报告、摘要和可导出的项目资产。",
  knowledge: "企业知识访问入口，承接授权后的知识检索与浏览。",
  projects: "Project 是唯一正式执行边界，协作、审批和审计都归属于它。",
  recent: "查看最近的对话、项目回访和最近进入的工作上下文。",
  schedules: "定时任务负责周期性执行、汇总和自动化调度。",
}

function PlaceholderView({
  icon,
  title,
  description,
  action,
}: {
  icon: ReactNode
  title: string
  description: string
  action: string
}) {
  return (
    <div className="flex min-h-full items-start justify-center bg-muted/30 p-4 md:p-6">
      <Card className="w-full max-w-3xl border-none bg-card shadow-sm">
        <CardHeader className="gap-3 border-b">
          <div className="flex size-12 items-center justify-center rounded-2xl border bg-muted/40 text-muted-foreground">
            {icon}
          </div>
          <div className="flex flex-col gap-1">
            <CardTitle className="text-2xl">{title}</CardTitle>
            <CardDescription className="text-sm leading-6">{description}</CardDescription>
          </div>
        </CardHeader>
        <CardContent className="flex flex-col gap-4 pt-5">
          <div className="rounded-2xl border bg-muted/30 p-4">
            <p className="text-sm font-medium text-foreground">当前阶段先做结构落位</p>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              这块视图先与最新架构和术语对齐，再逐步接入真实数据和交互流。
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button>{action}</Button>
            <Button variant="outline">查看相关文档</Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

function PageHeader({
  activeView,
  onStartChat,
}: {
  activeView: SidebarView
  onStartChat: () => void
}) {
  const isWorkbench = activeView === "workbench"

  return (
    <header className="sticky top-[64px] z-20 border-b border-border bg-background/95 backdrop-blur md:top-0">
      <div className="flex flex-col gap-4 px-4 py-4 md:px-6">
        <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
          <div className="flex flex-col gap-1">
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <span>SwarmMind</span>
              <span>/</span>
              <span className="text-foreground">{VIEW_LABELS[activeView]}</span>
            </div>
            <div>
              <h1 className="text-xl font-semibold tracking-tight text-foreground md:text-2xl">
                {VIEW_LABELS[activeView]}
              </h1>
              <p className="mt-1 text-sm text-muted-foreground">{viewDescriptions[activeView]}</p>
            </div>
          </div>

          <div className="flex flex-col gap-3 md:flex-row md:items-center">
            <div className="relative min-w-0 md:w-[320px]">
              <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                readOnly
                value=""
                placeholder="全局搜索项目、会话、产物"
                className="h-10 rounded-xl bg-muted/30 pl-9"
              />
            </div>
            <div className="flex items-center gap-2">
              {isWorkbench ? (
                <>
                  <Button variant="outline" size="lg">
                    我的范围
                  </Button>
                  <Button variant="outline" size="lg">
                    查看待审批
                  </Button>
                  <Button size="lg">新建项目</Button>
                </>
              ) : (
                <>
                  <Button variant="outline" size="lg" onClick={onStartChat}>
                    新建对话
                  </Button>
                  <Button size="lg">主动作</Button>
                </>
              )}
            </div>
          </div>
        </div>
      </div>
    </header>
  )
}

export default function App() {
  const [activeView, setActiveView] = useState<SidebarView>("workbench")
  const [activeConversationId, setActiveConversationId] = useState<string | undefined>(undefined)

  const handleViewChange = (view: SidebarView) => {
    setActiveView(view)
    if (view !== "chat") {
      setActiveConversationId(undefined)
    }
  }

  const handleStartChat = () => {
    setActiveConversationId(undefined)
    setActiveView("chat")
  }

  const renderContent = () => {
    switch (activeView) {
      case "workbench":
        return (
          <Workbench
            onStartChat={handleStartChat}
            onOpenProjects={() => handleViewChange("projects")}
            onOpenApprovals={() => handleViewChange("recent")}
          />
        )
      case "chat":
        return (
          <V0Chat
            conversationId={activeConversationId}
            onConversationCreated={(id) => {
              setActiveConversationId(id)
            }}
          />
        )
      case "teams":
        return (
          <PlaceholderView
            icon={<Bot className="size-5" />}
            title="Agent Team"
            description="这里承接 Team 模板的配置和治理。用户看到的是 Team 概念，项目里挂载的是项目级 Team 实例。"
            action="新建 Team 模板"
          />
        )
      case "skills":
        return (
          <PlaceholderView
            icon={<Sparkles className="size-5" />}
            title="技能中心"
            description="统一查看 MCP、Skills、绑定关系和最近调用状态。"
            action="新建绑定"
          />
        )
      case "assets":
        return (
          <PlaceholderView
            icon={<Library className="size-5" />}
            title="资源库"
            description="集中管理项目产物、导出结果、复盘总结和其他正式资产。"
            action="查看最近产物"
          />
        )
      case "knowledge":
        return (
          <PlaceholderView
            icon={<BookOpenText className="size-5" />}
            title="知识库"
            description="面向授权知识访问、检索和浏览，不等于运行时记忆本身。"
            action="连接知识源"
          />
        )
      case "projects":
        return (
          <PlaceholderView
            icon={<FolderKanban className="size-5" />}
            title="项目"
            description="正式执行、Team 实例挂载、审批和审计都应该在项目空间里闭环。"
            action="新建项目"
          />
        )
      case "recent":
        return (
          <PlaceholderView
            icon={<History className="size-5" />}
            title="最近记录"
            description="聚合你最近进入的 ChatSession、项目和回访上下文。"
            action="继续最近对话"
          />
        )
      case "schedules":
        return (
          <PlaceholderView
            icon={<Clock3 className="size-5" />}
            title="定时任务"
            description="配置周期执行、自动汇总和需要定时运行的工作流入口。"
            action="新建定时任务"
          />
        )
      default:
        return null
    }
  }

  return (
    <div className="min-h-screen bg-background">
      <Sidebar activeView={activeView} onViewChange={handleViewChange} pageTitle={VIEW_LABELS[activeView]} />

      <main className="flex min-h-screen flex-col md:ml-[280px]">
        <PageHeader activeView={activeView} onStartChat={handleStartChat} />
        <div className="flex-1 pt-[64px] md:pt-0">{renderContent()}</div>
      </main>
    </div>
  )
}
