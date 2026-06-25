import { useState } from "react"
import type { LucideIcon } from "lucide-react"
import {
  FolderKanban,
  LogOut,
  MessageSquareText,
  PenSquare,
  ShieldCheck,
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
  SidebarMenuBadge,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar"
import { useAuth } from "@/hooks/useAuth"

export type SidebarView = "chat" | "projects" | "approvals"

interface Conversation {
  id: string
  title: string
  updated_at: string
}

interface SidebarProps {
  activeView: SidebarView
  onViewChange: (view: SidebarView) => void
  conversations: Conversation[]
  activeConversationId?: string
  onSelectConversation: (id: string) => void
  onDeleteConversation: (id: string) => Promise<void>
  onNewChat: () => void
  pendingApprovalsCount: number
}

export function AppSidebar({
  activeView,
  onViewChange,
  conversations,
  activeConversationId,
  onSelectConversation,
  onDeleteConversation,
  onNewChat,
  pendingApprovalsCount,
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

  const navItems: {
    view: SidebarView
    label: string
    icon: LucideIcon
    badge?: number
  }[] = [
    { view: "chat", label: "对话", icon: MessageSquareText },
    { view: "projects", label: "项目", icon: FolderKanban },
    {
      view: "approvals",
      label: "审批中心",
      icon: ShieldCheck,
      badge: pendingApprovalsCount > 0 ? pendingApprovalsCount : undefined,
    },
  ]

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader className="gap-0 px-3 pt-4 pb-3">
        {/* 品牌：极简，仅字标 + 副标，无彩色色块 */}
        <div className="flex items-center gap-2 px-2 pb-4">
          <div className="flex flex-col leading-tight">
            <span className="text-sm font-semibold tracking-tight text-sidebar-foreground">
              SwarmMind
            </span>
            <span className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground">
              Supervised Work Surface
            </span>
          </div>
        </div>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton
              onClick={onNewChat}
              className="h-8 text-sm text-sidebar-foreground"
            >
              <PenSquare className="size-4" />
              <span>新建任务</span>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>

      <SidebarContent className="px-3">
        <SidebarGroup className="px-0">
          <SidebarGroupContent>
            <SidebarMenu>
              {navItems.map((item) => (
                <SidebarMenuItem key={item.view}>
                  <SidebarMenuButton
                    isActive={activeView === item.view}
                    onClick={() => onViewChange(item.view)}
                    className="h-8 text-sm"
                  >
                    <item.icon className="size-4" />
                    <span>{item.label}</span>
                  </SidebarMenuButton>
                  {item.badge !== undefined && (
                    <SidebarMenuBadge>{item.badge > 9 ? "9+" : item.badge}</SidebarMenuBadge>
                  )}
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        <SidebarGroup className="flex-1 px-0">
          <SidebarGroupLabel className="px-2 text-[10px] uppercase tracking-[0.14em]">
            最近会话
          </SidebarGroupLabel>
          <SidebarGroupContent className="overflow-y-auto">
            <SidebarMenu>
              {conversations.slice(0, 6).map((conv) => (
                <SidebarMenuItem key={conv.id}>
                  <SidebarMenuButton
                    isActive={activeConversationId === conv.id}
                    onClick={() => onSelectConversation(conv.id)}
                    className="text-sm"
                  >
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
      </SidebarContent>

      {user && (
        <SidebarFooter className="border-t border-sidebar-border px-3 py-3">
          <SidebarMenu>
            <SidebarMenuItem>
              <div className="flex items-center gap-2 px-2">
                <Avatar size="sm" className="bg-sidebar-accent text-sidebar-foreground">
                  <AvatarFallback>
                    {(user.display_name ?? user.email).slice(0, 2).toUpperCase()}
                  </AvatarFallback>
                </Avatar>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-sidebar-foreground">
                    {user.display_name ?? user.email}
                  </p>
                  <p className="truncate text-xs text-muted-foreground">{user.email}</p>
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  className="size-8 text-muted-foreground hover:text-foreground"
                  onClick={() => void logout()}
                >
                  <LogOut className="size-4" />
                </Button>
              </div>
            </SidebarMenuItem>
          </SidebarMenu>
        </SidebarFooter>
      )}
    </Sidebar>
  )
}

export { AppSidebar as Sidebar }
