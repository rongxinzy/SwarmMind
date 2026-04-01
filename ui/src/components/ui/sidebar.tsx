"use client"

import * as React from "react"
import { AnimatePresence, motion } from "framer-motion"
import {
  BookOpenText,
  Bot,
  ChevronDown,
  Clock3,
  FolderKanban,
  History,
  Home,
  Library,
  Menu,
  Plus,
  Sparkles,
  X,
} from "lucide-react"

import { Button } from "@/components/ui/button"
import type { ConversationRecord } from "@/components/ui/v0-ai-chat"
import { cn } from "@/lib/utils"

export type SidebarView =
  | "workbench"
  | "chat"
  | "teams"
  | "skills"
  | "assets"
  | "knowledge"
  | "projects"
  | "recent"
  | "schedules"

export const VIEW_LABELS: Record<SidebarView, string> = {
  workbench: "工作台",
  chat: "AI 生成",
  teams: "Agent Team",
  skills: "技能中心",
  assets: "资源库",
  knowledge: "知识库",
  projects: "项目",
  recent: "最近记录",
  schedules: "定时任务",
}

const projectItems = [
  { label: "Enterprise CRM", meta: "进行中" },
  { label: "Recruiting Automation", meta: "待生成" },
  { label: "Partner Portal", meta: "待审批" },
]

const primaryItems: Array<{ value: SidebarView; label: string; icon: React.ReactNode }> = [
  { value: "workbench", label: "工作台", icon: <Home className="size-4" /> },
  { value: "chat", label: "AI 生成", icon: <Sparkles className="size-4" /> },
]

const capabilityItems: Array<{ value: SidebarView; label: string; icon: React.ReactNode }> = [
  { value: "projects", label: "项目", icon: <FolderKanban className="size-4" /> },
  { value: "teams", label: "Agent Team", icon: <Bot className="size-4" /> },
  { value: "skills", label: "技能中心", icon: <Sparkles className="size-4" /> },
  { value: "knowledge", label: "知识库", icon: <BookOpenText className="size-4" /> },
  { value: "assets", label: "资源库", icon: <Library className="size-4" /> },
]

const utilityItems: Array<{ value: SidebarView; label: string; icon: React.ReactNode }> = [
  { value: "recent", label: "最近记录", icon: <History className="size-4" /> },
  { value: "schedules", label: "定时任务", icon: <Clock3 className="size-4" /> },
]

function SectionLabel({ children }: { children: React.ReactNode }) {
  return <p className="px-3 text-[12px] leading-[18px] text-muted-foreground">{children}</p>
}

function NavButton({
  active,
  icon,
  label,
  badge,
  onClick,
}: {
  active?: boolean
  icon: React.ReactNode
  label: string
  badge?: string
  onClick: () => void
}) {
  return (
    <Button
      variant="ghost"
      onClick={onClick}
      className={cn(
        "h-9 w-full justify-start rounded-md px-3 text-left font-normal",
        active ? "bg-white text-foreground" : "text-muted-foreground hover:bg-white hover:text-foreground",
      )}
    >
      <span className={cn("mr-3 text-muted-foreground", active && "text-foreground")}>{icon}</span>
      <span className="flex-1 truncate text-[14px] leading-[22px]">{label}</span>
      {badge ? <span className="text-[12px] leading-[18px] text-muted-foreground">{badge}</span> : null}
    </Button>
  )
}

function formatConversationTime(value?: string) {
  if (!value) return ""
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ""

  return new Intl.DateTimeFormat("zh-CN", {
    month: "numeric",
    day: "numeric",
  }).format(date)
}

interface SidebarProps {
  activeView: SidebarView
  onViewChange: (view: SidebarView) => void
  recentConversations?: ConversationRecord[]
  onSelectConversation?: (id: string) => void
  pageTitle?: string
}

export function Sidebar({
  activeView,
  onViewChange,
  recentConversations = [],
  onSelectConversation,
  pageTitle,
}: SidebarProps) {
  const [isOpen, setIsOpen] = React.useState(false)

  const handleSelect = (view: SidebarView) => {
    onViewChange(view)
    setIsOpen(false)
  }

  const handleSelectConversation = (conversationId: string) => {
    onSelectConversation?.(conversationId)
    setIsOpen(false)
  }

  const sidebarContent = (
    <div className="flex h-full flex-col bg-sidebar">
      <div className="border-b border-sidebar-border px-4 py-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-[16px] leading-6 font-semibold text-foreground">SwarmMind</p>
            <p className="mt-1 text-[12px] leading-[18px] text-muted-foreground">Enterprise AI Workspace</p>
          </div>
          <span className="rounded-md bg-white px-2 py-1 text-[12px] leading-[18px] text-muted-foreground">
            v0.1
          </span>
        </div>
      </div>

      <div className="border-b border-sidebar-border px-4 py-4">
        <Button onClick={() => handleSelect("chat")} className="w-full justify-center">
          新建生成任务
        </Button>
      </div>

      <nav className="flex-1 overflow-y-auto px-3 py-4">
        <div className="space-y-6">
          <div className="space-y-2">
            <SectionLabel>入口</SectionLabel>
            <div className="space-y-1">
              {primaryItems.map((item) => (
                <NavButton
                  key={item.value}
                  active={activeView === item.value}
                  icon={item.icon}
                  label={item.label}
                  onClick={() => handleSelect(item.value)}
                />
              ))}
            </div>
          </div>

          <div className="space-y-2">
            <SectionLabel>工作模块</SectionLabel>
            <div className="space-y-1">
              {capabilityItems.map((item) => (
                <NavButton
                  key={item.value}
                  active={activeView === item.value}
                  icon={item.icon}
                  label={item.label}
                  onClick={() => handleSelect(item.value)}
                />
              ))}
            </div>
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between px-3">
              <SectionLabel>项目列表</SectionLabel>
              <Button variant="ghost" size="icon-xs" onClick={() => handleSelect("projects")}>
                <Plus className="size-3.5" />
              </Button>
            </div>
            <div className="space-y-1 rounded-lg border border-border bg-white p-2">
              {projectItems.map((project) => (
                <Button
                  key={project.label}
                  variant="ghost"
                  onClick={() => handleSelect("projects")}
                  className="h-auto w-full justify-start rounded-md px-2.5 py-2"
                >
                  <div className="min-w-0 flex-1 text-left">
                    <p className="truncate text-[14px] leading-[22px] text-foreground">{project.label}</p>
                    <p className="mt-0.5 text-[12px] leading-[18px] text-muted-foreground">{project.meta}</p>
                  </div>
                </Button>
              ))}
            </div>
          </div>

          <div className="space-y-2">
            <SectionLabel>最近与自动化</SectionLabel>
            <div className="space-y-1">
              {utilityItems.map((item) => (
                <NavButton
                  key={item.value}
                  active={activeView === item.value}
                  icon={item.icon}
                  label={item.label}
                  onClick={() => handleSelect(item.value)}
                />
              ))}
            </div>

            <div className="rounded-lg border border-border bg-white p-2">
              <p className="px-1 py-1 text-[12px] leading-[18px] text-muted-foreground">最近会话</p>
              {recentConversations.length > 0 ? (
                recentConversations.slice(0, 4).map((conversation) => (
                  <Button
                    key={conversation.id}
                    variant="ghost"
                    onClick={() => handleSelectConversation(conversation.id)}
                    className="mt-1 h-auto w-full justify-start rounded-md px-2.5 py-2"
                  >
                    <div className="min-w-0 flex-1 text-left">
                      <p className="truncate text-[14px] leading-[22px] text-foreground">{conversation.title}</p>
                      <p className="mt-0.5 text-[12px] leading-[18px] text-muted-foreground">
                        {formatConversationTime(conversation.updated_at)}
                      </p>
                    </div>
                  </Button>
                ))
              ) : (
                <div className="px-2.5 py-3 text-[12px] leading-[18px] text-muted-foreground">
                  还没有最近会话。
                </div>
              )}
            </div>
          </div>
        </div>
      </nav>

      <div className="border-t border-sidebar-border p-4">
        <Button variant="outline" className="h-auto w-full justify-start px-3 py-2.5">
          <div className="flex size-8 items-center justify-center rounded-md bg-secondary text-[12px] font-medium text-foreground">
            KL
          </div>
          <div className="ml-3 min-w-0 flex-1 text-left">
            <p className="truncate text-[14px] leading-[22px] text-foreground">Kr Li</p>
            <p className="truncate text-[12px] leading-[18px] text-muted-foreground">容芯开源组</p>
          </div>
          <ChevronDown className="size-4 text-muted-foreground" />
        </Button>
      </div>
    </div>
  )

  return (
    <>
      <AnimatePresence>
        {isOpen ? (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 z-40 bg-black/20 md:hidden"
              onClick={() => setIsOpen(false)}
            />
            <motion.div
              initial={{ x: "-100%" }}
              animate={{ x: 0 }}
              exit={{ x: "-100%" }}
              transition={{ type: "spring", damping: 24, stiffness: 280 }}
              className="fixed inset-y-0 left-0 z-50 w-[236px] border-r border-sidebar-border bg-sidebar md:hidden"
            >
              <div className="flex items-center justify-between border-b border-sidebar-border px-4 py-4">
                <span className="text-[16px] font-semibold text-foreground">SwarmMind</span>
                <Button variant="icon" size="icon-sm" onClick={() => setIsOpen(false)}>
                  <X className="size-4" />
                </Button>
              </div>
              {sidebarContent}
            </motion.div>
          </>
        ) : null}
      </AnimatePresence>

      <aside className="fixed inset-y-0 left-0 hidden w-[236px] border-r border-sidebar-border bg-sidebar md:block">
        {sidebarContent}
      </aside>

      <div className="fixed left-0 right-0 top-0 z-30 border-b border-sidebar-border bg-background md:hidden">
        <div className="flex items-center justify-between px-4 py-4">
          <span className="truncate text-[16px] font-semibold text-foreground">{pageTitle || "SwarmMind"}</span>
          <Button variant="icon" size="icon-sm" onClick={() => setIsOpen(true)}>
            <Menu className="size-4" />
          </Button>
        </div>
      </div>
    </>
  )
}
