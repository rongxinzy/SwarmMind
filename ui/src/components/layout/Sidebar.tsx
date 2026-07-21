import { useState } from "react"
import type { LucideIcon } from "lucide-react"
import {
  FolderKanban,
  LogOut,
  MessageSquareText,
  PenSquare,
  ServerCog,
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

export type SidebarView = "chat" | "projects" | "providers"

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
}

export function AppSidebar({
  activeView,
  onViewChange,
  conversations,
  activeConversationId,
  onSelectConversation,
  onDeleteConversation,
  onNewChat,
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
  }[] = [
    { view: "chat", label: "任务", icon: MessageSquareText },
    { view: "projects", label: "项目", icon: FolderKanban },
    { view: "providers", label: "算力", icon: ServerCog },
  ]

  return (
    <Sidebar collapsible="icon" className="border-r border-[#e8e8e8]">
      <SidebarHeader className="gap-2 px-2 pb-3 pt-4">
        <div className="flex items-center gap-2 px-1 pb-3 group-data-[collapsible=icon]:justify-center">
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
              Deliverable Workbench
            </span>
          </div>
        </div>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton
              onClick={onNewChat}
              tooltip="新任务"
              aria-label="新任务"
              className="h-8 text-sm text-sidebar-foreground"
            >
              <PenSquare className="size-4" />
              <span className="group-data-[collapsible=icon]:hidden">新任务</span>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>

      <SidebarContent className="px-2">
        <SidebarGroup className="px-0">
          <SidebarGroupContent>
            <SidebarMenu>
              {navItems.map((item) => (
                <SidebarMenuItem key={item.view}>
                  <SidebarMenuButton
                    isActive={activeView === item.view}
                    onClick={() => onViewChange(item.view)}
                    tooltip={item.label}
                    aria-label={item.label}
                    className="h-8 text-sm"
                  >
                    <item.icon className="size-4" />
                    <span className="group-data-[collapsible=icon]:hidden">{item.label}</span>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        <SidebarGroup className="flex-1 px-0 group-data-[collapsible=icon]:hidden">
          <SidebarGroupLabel className="px-2 text-xs">
            最近工作
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
                  <p className="truncate text-xs text-muted-foreground">{user.email}</p>
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  className="size-8 text-muted-foreground hover:text-foreground group-data-[collapsible=icon]:hidden"
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
