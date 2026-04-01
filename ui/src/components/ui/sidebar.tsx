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
} from "lucide-react"

import { Button } from "@/components/ui/button"
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
  chat: "新建对话",
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
  { label: "Recruiting Automation", meta: "设计中" },
  { label: "Partner Portal", meta: "阻塞" },
]

const recentItems = [
  { label: "CRM 报表范围是否纳入首期", meta: "1h" },
  { label: "GitLab MCP 接入方案", meta: "3h" },
  { label: "招聘流程自动化优先级", meta: "昨天" },
]

const primaryItems: Array<{ value: SidebarView; label: string; icon: React.ReactNode }> = [
  { value: "workbench", label: "工作台", icon: <Home className="size-4" /> },
]

const capabilityItems: Array<{ value: SidebarView; label: string; icon: React.ReactNode }> = [
  { value: "teams", label: "Agent Team", icon: <Bot className="size-4" /> },
  { value: "skills", label: "技能中心", icon: <Sparkles className="size-4" /> },
  { value: "assets", label: "资源库", icon: <Library className="size-4" /> },
  { value: "knowledge", label: "知识库", icon: <BookOpenText className="size-4" /> },
]

const utilityItems: Array<{ value: SidebarView; label: string; icon: React.ReactNode }> = [
  { value: "schedules", label: "定时任务", icon: <Clock3 className="size-4" /> },
]

const XIcon = () => (
  <motion.svg
    width="16"
    height="16"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
  >
    <motion.line x1="18" y1="6" x2="6" y2="18" />
    <motion.line x1="6" y1="6" x2="18" y2="18" />
  </motion.svg>
)

const SwarmLogo = ({ className = "size-5" }: { className?: string }) => (
  <svg className={className} viewBox="0 0 13 13" fill="none">
    <path
      d="M6.5 1L11.5 4v5L6.5 12 1.5 9V4L6.5 1Z"
      stroke="currentColor"
      strokeWidth="1.4"
      strokeLinejoin="round"
    />
    <circle cx="6.5" cy="6.5" r="1.5" fill="currentColor" />
  </svg>
)

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
    <button
      onClick={onClick}
      className={cn(
        "flex w-full items-center gap-2 rounded-xl px-2.5 py-2 text-[13px] transition-colors",
        active
          ? "bg-sidebar-accent text-sidebar-accent-foreground"
          : "text-muted-foreground hover:bg-secondary hover:text-foreground"
      )}
    >
      <span className="opacity-70">{icon}</span>
      <span className="truncate">{label}</span>
      {badge ? (
        <span className="ml-auto rounded-full border border-border px-1.5 py-0.5 text-[10px] text-muted-foreground">
          {badge}
        </span>
      ) : null}
    </button>
  )
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <p className="px-2.5 text-[10px] font-medium uppercase tracking-[0.22em] text-muted-foreground/70">
      {children}
    </p>
  )
}

interface SidebarProps {
  activeView: SidebarView
  onViewChange: (view: SidebarView) => void
  pageTitle?: string
}

export function Sidebar({ activeView, onViewChange, pageTitle }: SidebarProps) {
  const [isOpen, setIsOpen] = React.useState(false)

  const handleSelect = (view: SidebarView) => {
    onViewChange(view)
    setIsOpen(false)
  }

  const sidebarContent = (
    <div className="flex h-full flex-col">
      <div className="flex h-[60px] items-center gap-3 border-b border-sidebar-border px-4">
        <div className="flex size-8 items-center justify-center rounded-xl bg-foreground text-background">
          <SwarmLogo className="size-4" />
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-sm font-semibold tracking-tight text-foreground">SwarmMind</p>
          <p className="text-[11px] text-muted-foreground">Supervisor Console</p>
        </div>
        <span className="rounded-full border border-sidebar-border px-2 py-1 font-mono text-[10px] text-muted-foreground">
          v0.1
        </span>
      </div>

      <div className="border-b border-sidebar-border px-3 py-3">
        <Button
          onClick={() => handleSelect("chat")}
          className="w-full justify-start gap-2 text-[13px]"
          size="lg"
        >
          <Plus className="size-4" />
          新建对话
        </Button>
      </div>

      <nav className="flex-1 overflow-y-auto px-2 py-3">
        <div className="flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <SectionLabel>首页</SectionLabel>
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

          <div className="flex flex-col gap-1.5">
            <SectionLabel>能力与配置</SectionLabel>
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

          <div className="flex flex-col gap-1.5">
            <div className="flex items-center justify-between px-2.5">
              <SectionLabel>项目</SectionLabel>
              <button className="rounded-md p-1 text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground">
                <Plus className="size-3.5" />
              </button>
            </div>
            <NavButton
              active={activeView === "projects"}
              icon={<FolderKanban className="size-4" />}
              label="项目列表"
              badge="12"
              onClick={() => handleSelect("projects")}
            />
            <div className="flex flex-col gap-1">
              {projectItems.map((project) => (
                <button
                  key={project.label}
                  onClick={() => handleSelect("projects")}
                  className="flex items-center gap-2 rounded-xl px-2.5 py-2 text-left text-[13px] text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
                >
                  <span className="min-w-0 flex-1 truncate">{project.label}</span>
                  <span className="text-[10px] text-muted-foreground">{project.meta}</span>
                </button>
              ))}
            </div>
          </div>

          <div className="flex flex-col gap-1.5">
            <SectionLabel>最近</SectionLabel>
            <NavButton
              active={activeView === "recent"}
              icon={<History className="size-4" />}
              label="最近记录"
              onClick={() => handleSelect("recent")}
            />
            <div className="flex flex-col gap-1">
              {recentItems.map((item) => (
                <button
                  key={item.label}
                  onClick={() => handleSelect("recent")}
                  className="flex items-center gap-2 rounded-xl px-2.5 py-2 text-left text-[13px] text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
                >
                  <span className="min-w-0 flex-1 truncate">{item.label}</span>
                  <span className="text-[10px] text-muted-foreground">{item.meta}</span>
                </button>
              ))}
            </div>
          </div>

          <div className="flex flex-col gap-1.5">
            <SectionLabel>自动化</SectionLabel>
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
        </div>
      </nav>

      <div className="border-t border-sidebar-border p-3">
        <button className="flex w-full items-center gap-3 rounded-xl px-2.5 py-2 transition-colors hover:bg-secondary">
          <div className="flex size-8 items-center justify-center rounded-full border border-border bg-secondary text-xs font-semibold text-foreground">
            KL
          </div>
          <div className="min-w-0 flex-1 text-left">
            <p className="truncate text-[13px] font-medium text-foreground">Kr Li</p>
            <p className="truncate text-[11px] text-muted-foreground">容芯开源组</p>
          </div>
          <ChevronDown className="size-4 text-muted-foreground" />
        </button>
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
              className="fixed inset-0 z-40 bg-black/40 md:hidden"
              onClick={() => setIsOpen(false)}
            />
            <motion.div
              initial={{ x: "-100%" }}
              animate={{ x: 0 }}
              exit={{ x: "-100%" }}
              transition={{ type: "spring", damping: 24, stiffness: 220 }}
              className="fixed inset-y-0 left-0 z-50 w-[280px] border-r border-sidebar-border bg-sidebar md:hidden"
            >
              <div className="flex items-center justify-between border-b border-sidebar-border px-4 py-4">
                <div className="flex items-center gap-3">
                  <div className="flex size-8 items-center justify-center rounded-xl bg-foreground text-background">
                    <SwarmLogo className="size-4" />
                  </div>
                  <span className="text-sm font-semibold text-foreground">SwarmMind</span>
                </div>
                <Button variant="ghost" size="icon" onClick={() => setIsOpen(false)}>
                  <XIcon />
                </Button>
              </div>
              {sidebarContent}
            </motion.div>
          </>
        ) : null}
      </AnimatePresence>

      <div className="fixed inset-y-0 left-0 hidden w-[280px] border-r border-sidebar-border bg-sidebar md:flex md:flex-col">
        {sidebarContent}
      </div>

      <div className="fixed left-0 right-0 top-0 z-30 border-b border-sidebar-border bg-sidebar md:hidden">
        <div className="flex items-center justify-between px-4 py-4">
          <div className="flex items-center gap-3">
            <div className="flex size-8 items-center justify-center rounded-xl bg-foreground text-background">
              <SwarmLogo className="size-4" />
            </div>
            <span className="text-sm font-semibold text-foreground">{pageTitle || "SwarmMind"}</span>
          </div>
          <Button variant="ghost" size="icon" onClick={() => setIsOpen(true)}>
            <Menu className="size-5" />
          </Button>
        </div>
      </div>
    </>
  )
}
