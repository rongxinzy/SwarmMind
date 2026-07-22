import { useState } from "react"
import type { LucideIcon } from "lucide-react"
import {
  Building2,
  FolderKanban,
  LogOut,
  MessageSquareText,
  PenSquare,
  Plus,
  Settings,
  Trash2,
} from "lucide-react"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Button } from "@/components/ui/button"
import { Spinner } from "@/components/ui/spinner"
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuAction,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar"
import { useAuth } from "@/hooks/useAuth"

export type AppMode = "chat" | "work"
export type WorkView = "tasks" | "projects"

interface Conversation {
  id: string
  title: string
  updated_at: string
}

interface Project {
  project_id: string
  title: string
}

interface SidebarProps {
  mode: AppMode
  workView: WorkView
  onModeChange: (mode: AppMode) => void
  onWorkViewChange: (view: WorkView) => void
  conversations: Conversation[]
  projects: Project[]
  activeConversationId?: string
  activeProjectId?: string
  onSelectConversation: (id: string) => void
  onDeleteConversation: (id: string) => Promise<void>
  onSelectProject: (id: string) => void
  onNewChat: () => void
  onNewTask: () => void
  onNewProject: () => void
  onOpenAdmin: () => void
}

export function AppSidebar({
  mode,
  workView,
  onModeChange,
  onWorkViewChange,
  conversations,
  projects,
  activeConversationId,
  activeProjectId,
  onSelectConversation,
  onDeleteConversation,
  onSelectProject,
  onNewChat,
  onNewTask,
  onNewProject,
  onOpenAdmin,
}: SidebarProps) {
  const { user, logout } = useAuth()
  const [deletingId, setDeletingId] = useState<string | null>(null)

  async function handleDelete(id: string, e: React.MouseEvent) {
    e.stopPropagation()
    if (!window.confirm("删除这个会话后，消息记录将一并移除。是否继续？")) return
    setDeletingId(id)
    try {
      await onDeleteConversation(id)
    } finally {
      setDeletingId(null)
    }
  }

  const isAdmin = user?.role === "admin"

  return (
    <Sidebar collapsible="icon" className="border-r border-[#e8e8e8]">
      <SidebarHeader className="gap-2 px-2 pb-3 pt-4">
        <div className="flex items-center gap-2 px-1 pb-2 group-data-[collapsible=icon]:justify-center">
          <div className="grid size-8 shrink-0 grid-cols-2 gap-0.5 rounded-lg bg-[#141414] p-1.5">
            <span className="rounded-[3px] bg-white" />
            <span className="rounded-[3px] bg-white/65" />
            <span className="rounded-[3px] bg-white/65" />
            <span className="rounded-[3px] bg-white" />
          </div>
          <div className="flex flex-col leading-tight group-data-[collapsible=icon]:hidden">
            <span className="text-sm font-semibold text-sidebar-foreground">
              SwarmMind
            </span>
            <span className="text-[11px] text-muted-foreground">
              Agent Chat
            </span>
          </div>
        </div>

        <div className="group-data-[collapsible=icon]:hidden">
          <ModeSwitch mode={mode} onChange={onModeChange} />
        </div>

        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton
              onClick={mode === "chat" ? onNewChat : onNewTask}
              tooltip={mode === "chat" ? "新对话" : "新任务"}
              aria-label={mode === "chat" ? "新对话" : "新任务"}
              className="h-8 text-sm text-sidebar-foreground"
            >
              <PenSquare className="size-4" />
              <span className="group-data-[collapsible=icon]:hidden">{mode === "chat" ? "新对话" : "新任务"}</span>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>

      <SidebarContent className="px-2">
        {mode === "work" ? (
          <>
            <SidebarGroup className="px-0">
              <SidebarGroupLabel className="px-2 text-xs">任务会话</SidebarGroupLabel>
              <SidebarGroupContent className="overflow-y-auto">
                <SidebarMenu>
                  {conversations.slice(0, 8).map((conv) => (
                    <SidebarMenuItem key={conv.id}>
                      <SidebarMenuButton
                        isActive={workView === "tasks" && activeConversationId === conv.id}
                        onClick={() => {
                          onWorkViewChange("tasks")
                          onSelectConversation(conv.id)
                        }}
                        className="text-sm"
                      >
                        <MessageSquareText className="size-4" />
                        <span className="truncate">{conv.title}</span>
                      </SidebarMenuButton>
                      <SidebarMenuAction
                        showOnHover
                        disabled={deletingId === conv.id}
                        onClick={(e: React.MouseEvent<HTMLButtonElement>) =>
                          void handleDelete(conv.id, e)
                        }
                      >
                        {deletingId === conv.id ? <Spinner /> : <Trash2 />}
                      </SidebarMenuAction>
                    </SidebarMenuItem>
                  ))}
                </SidebarMenu>
              </SidebarGroupContent>
            </SidebarGroup>

            <SidebarGroup className="flex-1 px-0">
              <div className="flex items-center justify-between px-2">
                <SidebarGroupLabel className="px-0 text-xs">项目</SidebarGroupLabel>
                <button
                  type="button"
                  onClick={onNewProject}
                  className="rounded p-0.5 text-sidebar-foreground/70 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
                  aria-label="新建项目"
                  title="新建项目"
                >
                  <Plus className="size-3.5" />
                </button>
              </div>
              <SidebarGroupContent className="overflow-y-auto">
                <SidebarMenu>
                  {projects.slice(0, 8).map((project) => (
                    <SidebarMenuItem key={project.project_id}>
                      <SidebarMenuButton
                        isActive={workView === "projects" && activeProjectId === project.project_id}
                        onClick={() => {
                          onWorkViewChange("projects")
                          onSelectProject(project.project_id)
                        }}
                        className="text-sm"
                      >
                        <FolderKanban className="size-4" />
                        <span className="truncate">{project.title}</span>
                      </SidebarMenuButton>
                    </SidebarMenuItem>
                  ))}
                </SidebarMenu>
              </SidebarGroupContent>
            </SidebarGroup>
          </>
        ) : (
          <SidebarGroup className="flex-1 px-0">
            <SidebarGroupLabel className="px-2 text-xs">最近对话</SidebarGroupLabel>
            <SidebarGroupContent className="overflow-y-auto">
              <SidebarMenu>
                {conversations.slice(0, 10).map((conv) => (
                  <SidebarMenuItem key={conv.id}>
                    <SidebarMenuButton
                      isActive={activeConversationId === conv.id}
                      onClick={() => onSelectConversation(conv.id)}
                      className="text-sm"
                    >
                      <MessageSquareText className="size-4" />
                      <span className="truncate">{conv.title}</span>
                    </SidebarMenuButton>
                    <SidebarMenuAction
                      showOnHover
                      disabled={deletingId === conv.id}
                      onClick={(e: React.MouseEvent<HTMLButtonElement>) =>
                        void handleDelete(conv.id, e)
                      }
                    >
                      {deletingId === conv.id ? <Spinner /> : <Trash2 />}
                    </SidebarMenuAction>
                  </SidebarMenuItem>
                ))}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        )}
      </SidebarContent>

      {user && (
        <SidebarFooter className="border-t border-sidebar-border px-3 py-3">
          <SidebarMenu>
            <SidebarMenuItem>
              <div className="flex items-center gap-2 px-2 group-data-[collapsible=icon]:justify-center group-data-[collapsible=icon]:px-0">
                <Avatar size="sm" className="bg-sidebar-accent text-sidebar-foreground">
                  <AvatarFallback>
                    {(user.display_name ?? user.email).slice(0, 2).toUpperCase()}
                  </AvatarFallback>
                </Avatar>
                <div className="min-w-0 flex-1 group-data-[collapsible=icon]:hidden">
                  <p className="truncate text-sm font-medium text-sidebar-foreground">
                    {user.display_name ?? user.email}
                  </p>
                  <p className="truncate text-xs text-muted-foreground">
                    {isAdmin ? "管理员" : "成员"}
                  </p>
                </div>
                <div className="flex items-center gap-0.5 group-data-[collapsible=icon]:hidden">
                  {isAdmin && (
                    <Button
                      variant="ghost"
                      size="icon"
                      className="size-8 text-muted-foreground hover:text-foreground"
                      onClick={() => onOpenAdmin()}
                      aria-label="组织管理"
                      title="组织管理"
                    >
                      <Building2 className="size-4" />
                    </Button>
                  )}
                  <Button
                    variant="ghost"
                    size="icon"
                    className="size-8 text-muted-foreground hover:text-foreground"
                    onClick={() => void logout()}
                    aria-label="退出"
                    title="退出"
                  >
                    <LogOut className="size-4" />
                  </Button>
                </div>
              </div>
            </SidebarMenuItem>
          </SidebarMenu>
        </SidebarFooter>
      )}
    </Sidebar>
  )
}

function ModeSwitch({ mode, onChange }: { mode: AppMode; onChange: (mode: AppMode) => void }) {
  return (
    <div className="flex items-center rounded-full bg-[#ededed] p-0.5">
      <ModePill active={mode === "work"} onClick={() => onChange("work")} icon={MessageSquareText} label="Work" />
      <ModePill active={mode === "chat"} onClick={() => onChange("chat")} icon={Settings} label="Chat" />
    </div>
  )
}

function ModePill({
  active,
  onClick,
  icon: Icon,
  label,
}: {
  active: boolean
  onClick: () => void
  icon: LucideIcon
  label: string
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`flex flex-1 items-center justify-center gap-1.5 rounded-full px-2 py-1 text-xs font-medium transition-colors ${
        active
          ? "bg-white text-[#141414] shadow-[0_1px_2px_rgba(0,0,0,0.05)]"
          : "text-[#5d5d5d] hover:text-[#141414]"
      }`}
      aria-pressed={active}
    >
      <Icon className="size-3.5" />
      {label}
    </button>
  )
}

export { AppSidebar as Sidebar }
