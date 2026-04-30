"use client"

import * as React from "react"
import { AnimatePresence, motion } from "framer-motion"
import {
  Building2,
  BookOpenText,
  Bot,
  Clock3,
  ChevronDown,
  ChevronRight,
  FolderKanban,
  History,
  Library,
  Loader2,
  Menu,
  MessageSquareText,
  PenSquare,
  PanelLeftClose,
  PanelLeftOpen,
  Sparkles,
  Trash2,
  X,
} from "lucide-react"

import { Button } from "@/components/ui/button"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
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
  chat: "对话",
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

const primaryItems: { value: SidebarView; label: string; icon: React.ReactNode }[] = [
  { value: "workbench", label: "新建任务", icon: <PenSquare className="size-4" /> },
  { value: "chat", label: "对话", icon: <MessageSquareText className="size-4" /> },
]

const capabilityItems: { value: SidebarView; label: string; icon: React.ReactNode }[] = [
  { value: "projects", label: "项目", icon: <FolderKanban className="size-4" /> },
  { value: "teams", label: "Agent Team", icon: <Bot className="size-4" /> },
  { value: "skills", label: "技能中心", icon: <Sparkles className="size-4" /> },
  { value: "knowledge", label: "知识库", icon: <BookOpenText className="size-4" /> },
  { value: "assets", label: "资源库", icon: <Library className="size-4" /> },
]

const utilityItems: { value: SidebarView; label: string; icon: React.ReactNode }[] = [
  { value: "recent", label: "最近记录", icon: <History className="size-4" /> },
  { value: "schedules", label: "定时任务", icon: <Clock3 className="size-4" /> },
]

function projectMetaClassName(meta: string) {
  if (meta === "进行中") return "text-[var(--status-running)]"
  if (meta === "待审批") return "text-[var(--status-approval)]"
  return "text-muted-foreground"
}

function SectionLabel({
  children,
  className,
}: {
  children: React.ReactNode
  className?: string
}) {
  return (
    <p className={cn("px-3 text-[15px] leading-6 font-semibold tracking-[-0.01em] text-muted-foreground", className)}>
      {children}
    </p>
  )
}

function SectionHeaderButton({
  children,
  open,
  className,
}: {
  children: React.ReactNode
  open: boolean
  className?: string
}) {
  return (
    <div
      className={cn(
        "flex w-full items-center justify-between rounded-xl px-3 py-1 text-left transition-colors hover:bg-sidebar-accent/50",
        className,
      )}
    >
      <SectionLabel className="px-0">{children}</SectionLabel>
      <ChevronDown
        className={cn(
          "size-4 shrink-0 text-muted-foreground transition-transform duration-200",
          !open && "-rotate-90",
        )}
      />
    </div>
  )
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
        "relative min-h-10 w-full justify-start rounded-xl border px-3 py-2 text-left font-normal transition-colors",
        active
          ? "border-sidebar-border/70 bg-sidebar-accent text-foreground"
          : "border-transparent text-foreground hover:bg-sidebar-accent/70 hover:text-foreground",
      )}
    >
      {active ? (
        <span className="absolute left-1.5 top-1/2 h-5 w-[2px] -translate-y-1/2 rounded-full bg-accent" />
      ) : null}
      <span className={cn("mr-2 text-muted-foreground/90", active && "text-foreground")}>{icon}</span>
      <span className="flex-1 truncate text-[13px] leading-5">{label}</span>
      {badge ? <span className="text-[11px] leading-4 text-muted-foreground">{badge}</span> : null}
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

function SidebarHeader({
  onClose,
  onCollapse,
}: {
  onClose?: () => void
  onCollapse?: () => void
}) {
  return (
    <div className="px-4 py-4">
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 items-center gap-3">
          <div className="flex size-10 shrink-0 items-center justify-center rounded-2xl border border-sidebar-border bg-background text-foreground">
            <Sparkles className="size-4" />
          </div>
          <div className="min-w-0">
            <p className="truncate text-[14px] font-semibold tracking-[-0.02em] text-foreground">
              SwarmMind
            </p>
            <p className="mt-0.5 truncate text-[11px] leading-4 tracking-[0.04em] text-muted-foreground">
              SUPERVISED WORK SURFACE
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {onCollapse ? (
            <Button
              variant="ghost"
              size="icon-sm"
              onClick={onCollapse}
              className="hidden shrink-0 rounded-xl md:inline-flex"
              title="收起侧边栏"
            >
              <PanelLeftClose className="size-4" />
            </Button>
          ) : null}
          {onClose ? (
            <Button variant="icon" size="icon-sm" onClick={onClose} className="shrink-0 rounded-xl">
              <X className="size-4" />
            </Button>
          ) : null}
        </div>
      </div>
    </div>
  )
}

interface SidebarProps {
  activeView: SidebarView
  onViewChange: (view: SidebarView) => void
  isCollapsed?: boolean
  onCollapsedChange?: (collapsed: boolean) => void
  recentConversations?: ConversationRecord[]
  onSelectConversation?: (id: string) => void
  onDeleteConversation?: (id: string) => Promise<void>
  pageTitle?: string
  searchQuery?: string
  isRecentLoading?: boolean
  activeConversationId?: string
}

export function Sidebar({
  activeView,
  onViewChange,
  isCollapsed = false,
  onCollapsedChange,
  recentConversations = [],
  onSelectConversation,
  onDeleteConversation,
  pageTitle,
  searchQuery = "",
  isRecentLoading = false,
  activeConversationId,
}: SidebarProps) {
  const [isOpen, setIsOpen] = React.useState(false)
  const [deletingConversationId, setDeletingConversationId] = React.useState<string | null>(null)
  const [projectsOpen, setProjectsOpen] = React.useState(true)
  const [utilityOpen, setUtilityOpen] = React.useState(true)
  const [conversationsOpen, setConversationsOpen] = React.useState(true)

  const handleSelect = (view: SidebarView) => {
    onViewChange(view)
    setIsOpen(false)
  }

  const railItems: { value: SidebarView; icon: React.ReactNode; label: string }[] = [
    { value: "workbench", icon: <PenSquare className="size-[18px]" />, label: "新建任务" },
    { value: "chat", icon: <MessageSquareText className="size-[18px]" />, label: "对话" },
    { value: "knowledge", icon: <BookOpenText className="size-[18px]" />, label: "知识库" },
    { value: "assets", icon: <Library className="size-[18px]" />, label: "资源库" },
    { value: "recent", icon: <History className="size-[18px]" />, label: "最近记录" },
  ]

  const railBottomItems: { value: SidebarView; icon: React.ReactNode; label: string }[] = [
    { value: "projects", icon: <FolderKanban className="size-[18px]" />, label: "项目" },
    { value: "schedules", icon: <Clock3 className="size-[18px]" />, label: "定时任务" },
  ]

  const handleSelectConversation = (conversationId: string) => {
    onSelectConversation?.(conversationId)
    setIsOpen(false)
  }

  const handleDeleteConversation = async (conversationId: string) => {
    if (!onDeleteConversation) {
      return
    }

    const confirmed = window.confirm("删除这个会话后，消息记录将一并移除。是否继续？")
    if (!confirmed) {
      return
    }

    setDeletingConversationId(conversationId)
    try {
      await onDeleteConversation(conversationId)
    } catch (error) {
      console.error("Failed to delete conversation:", error)
    } finally {
      setDeletingConversationId(null)
    }
  }

  const sidebarContent = (options?: { onClose?: () => void }) => (
    <div
      className="flex h-full flex-col text-sidebar-foreground backdrop-blur-md"
      style={{ backgroundColor: "rgba(243, 243, 242, 0.94)" }}
    >
      <SidebarHeader
        onClose={options?.onClose}
        onCollapse={options?.onClose ? undefined : () => { onCollapsedChange?.(true); }}
      />
      <nav
        className="sidebar-scroll flex-1 overflow-y-auto px-3 py-4"
        style={{
          scrollbarWidth: "thin",
          scrollbarColor: "rgba(60, 60, 67, 0.22) transparent",
        }}
      >
        <div className="space-y-7">
          <div className="space-y-1">
            {primaryItems.map((item) => (
              <NavButton
                key={item.value}
                active={activeView === item.value}
                icon={item.icon}
                label={item.label}
                onClick={() => { handleSelect(item.value); }}
              />
            ))}
          </div>

          <div className="space-y-2.5">
            <SectionLabel>工作模块</SectionLabel>
            <div className="space-y-1">
              {capabilityItems.map((item) => (
                <NavButton
                  key={item.value}
                  active={activeView === item.value}
                  icon={item.icon}
                  label={item.label}
                  onClick={() => { handleSelect(item.value); }}
                />
              ))}
            </div>
          </div>

          <Collapsible open={projectsOpen} onOpenChange={setProjectsOpen} className="space-y-2.5">
            <CollapsibleTrigger className="block w-full">
              <SectionHeaderButton open={projectsOpen}>项目列表</SectionHeaderButton>
            </CollapsibleTrigger>
            <CollapsibleContent className="space-y-1">
              {projectItems.map((project) => (
                <Button
                  key={project.label}
                  variant="ghost"
                  onClick={() => { handleSelect("projects"); }}
                  className="h-auto min-h-10 w-full justify-start rounded-xl border border-transparent px-3 py-2 hover:bg-sidebar-accent/65"
                >
                  <div className="min-w-0 flex-1 text-left">
                    <p className="truncate text-[14px] leading-[22px] tracking-[-0.01em] text-foreground">{project.label}</p>
                    <p className={cn("mt-0.5 text-[11px] leading-4 tracking-[0.04em]", projectMetaClassName(project.meta))}>{project.meta}</p>
                  </div>
                </Button>
              ))}
            </CollapsibleContent>
          </Collapsible>

          <Collapsible open={utilityOpen} onOpenChange={setUtilityOpen} className="space-y-2.5">
            <CollapsibleTrigger className="block w-full">
              <SectionHeaderButton open={utilityOpen}>最近与自动化</SectionHeaderButton>
            </CollapsibleTrigger>
            <CollapsibleContent className="space-y-1">
              {utilityItems.map((item) => (
                <NavButton
                  key={item.value}
                  active={activeView === item.value}
                  icon={item.icon}
                  label={item.label}
                  onClick={() => { handleSelect(item.value); }}
                />
              ))}
            </CollapsibleContent>
          </Collapsible>

          <Collapsible open={conversationsOpen} onOpenChange={setConversationsOpen} className="space-y-2.5">
            <CollapsibleTrigger className="block w-full">
              <SectionHeaderButton open={conversationsOpen}>最近会话</SectionHeaderButton>
            </CollapsibleTrigger>
            <CollapsibleContent className="space-y-1.5">
              {isRecentLoading ? (
                <div className="space-y-2 px-3 py-2">
                  <div className="h-8 w-full animate-pulse rounded-md bg-sidebar-accent/60" />
                  <div className="h-8 w-full animate-pulse rounded-md bg-sidebar-accent/60" />
                  <div className="h-8 w-[80%] animate-pulse rounded-md bg-sidebar-accent/60" />
                </div>
              ) : recentConversations.length > 0 ? (
                recentConversations.slice(0, 4).map((conversation) => (
                  <div key={conversation.id} className="group flex items-center gap-1">
                    <Button
                      variant="ghost"
                      onClick={() => { handleSelectConversation(conversation.id); }}
                      className={cn(
                        "h-auto min-h-10 min-w-0 flex-1 justify-start rounded-xl border border-transparent px-3 py-2 hover:bg-sidebar-accent/65",
                        activeView === "chat" && conversation.id === activeConversationId
                          ? "bg-accent-soft border-l-2 border-l-accent"
                          : ""
                      )}
                    >
                      <div className="min-w-0 flex-1 text-left">
                        <p className="truncate text-[13px] leading-5 tracking-[-0.01em] text-foreground">{conversation.title}</p>
                        <p className="mt-0.5 text-[11px] leading-4 text-muted-foreground">
                          {formatConversationTime(conversation.updated_at)}
                        </p>
                      </div>
                    </Button>
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon-sm"
                      disabled={deletingConversationId === conversation.id}
                      onClick={(event) => {
                        event.stopPropagation()
                        void handleDeleteConversation(conversation.id)
                      }}
                      className="size-10 shrink-0 rounded-lg text-muted-foreground opacity-100 transition-colors hover:border-sidebar-border/60 hover:bg-sidebar-accent hover:text-destructive md:size-9 md:opacity-0 md:group-hover:opacity-100"
                      title="删除会话"
                    >
                      {deletingConversationId === conversation.id ? (
                        <Loader2 className="size-3.5 animate-spin" />
                      ) : (
                        <Trash2 className="size-3.5" />
                      )}
                    </Button>
                  </div>
                ))
              ) : (
                <div className="px-3 py-3 text-[12px] leading-[18px] text-muted-foreground">
                  {searchQuery.trim() ? "没有找到匹配的会话。" : "还没有最近会话。"}
                </div>
              )}
            </CollapsibleContent>
          </Collapsible>
        </div>
      </nav>

      <div className="border-t border-sidebar-border/80 px-3 pb-3 pt-3">
        <button
          type="button"
          className="flex w-full items-center gap-3 rounded-md border border-sidebar-border/70 bg-sidebar-accent/55 px-2.5 py-2 text-left transition-colors hover:bg-sidebar-accent"
        >
          <div className="flex size-7 shrink-0 items-center justify-center rounded-full border border-sidebar-border bg-sidebar text-[10px] font-medium tracking-[0.08em] text-foreground">
            KL
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-[12px] leading-5 font-medium tracking-[-0.01em] text-foreground">Keran Li</p>
            <div className="mt-px flex min-w-0 items-center gap-1.5 text-[10px] leading-4 tracking-[0.08em] text-muted-foreground">
              <Building2 className="size-3 shrink-0" />
              <span className="truncate">容芯开源组</span>
            </div>
          </div>
          <div className="flex size-6 shrink-0 items-center justify-center rounded-full text-muted-foreground/75 transition-colors group-hover/button:text-foreground">
            <ChevronRight className="size-3.5" />
          </div>
        </button>
      </div>
    </div>
  )

  const collapsedRail = (
    <div
      className="hidden h-full flex-col items-center px-3 py-4 md:flex"
      style={{ backgroundColor: "rgba(243, 243, 242, 0.94)" }}
    >
      <Button
        variant="ghost"
        size="icon"
        className="size-11 rounded-2xl bg-sidebar-accent/70 text-foreground hover:bg-sidebar-accent"
        onClick={() => { onCollapsedChange?.(false); }}
        title="展开侧边栏"
      >
        <PanelLeftOpen className="size-5" />
      </Button>

      <div className="mt-5 flex flex-col items-center gap-3">
        {railItems.map((item) => (
          <Button
            key={item.value}
            variant="ghost"
            size="icon"
            onClick={() => { handleSelect(item.value); }}
            title={item.label}
            className={cn(
              "size-11 rounded-2xl border border-transparent text-muted-foreground hover:bg-sidebar-accent/75 hover:text-foreground",
              activeView === item.value && "bg-sidebar-accent text-foreground",
            )}
          >
            {item.icon}
          </Button>
        ))}
      </div>

      <div className="mt-auto flex flex-col items-center gap-3">
        {railBottomItems.map((item) => (
          <Button
            key={item.value}
            variant="ghost"
            size="icon"
            onClick={() => { handleSelect(item.value); }}
            title={item.label}
            className={cn(
              "size-11 rounded-2xl border border-transparent text-muted-foreground hover:bg-sidebar-accent/75 hover:text-foreground",
              activeView === item.value && "bg-sidebar-accent text-foreground",
            )}
          >
            {item.icon}
          </Button>
        ))}
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
              onClick={() => { setIsOpen(false); }}
            />
            <motion.div
              initial={{ x: "-100%" }}
              animate={{ x: 0 }}
              exit={{ x: "-100%" }}
              transition={{ type: "spring", damping: 24, stiffness: 280 }}
              className="fixed inset-y-0 left-0 z-50 w-[248px] md:hidden"
            >
              {sidebarContent({ onClose: () => { setIsOpen(false); } })}
            </motion.div>
          </>
        ) : null}
      </AnimatePresence>

      <aside
        className={cn(
          "fixed inset-y-0 left-0 hidden transition-[width] duration-200 md:block",
          isCollapsed ? "w-[84px]" : "w-[248px]",
        )}
      >
        {isCollapsed ? collapsedRail : sidebarContent()}
      </aside>

      <div className="fixed left-0 right-0 top-0 z-30 border-b border-sidebar-border bg-background md:hidden">
        <div className="flex items-center justify-between px-4 py-4">
          <span className="truncate text-[16px] font-semibold text-foreground">{pageTitle || "SwarmMind"}</span>
          <Button variant="icon" size="icon-sm" onClick={() => { setIsOpen(true); }}>
            <Menu className="size-4" />
          </Button>
        </div>
      </div>
    </>
  )
}
