import { useCallback, useEffect, useState } from "react"
import { AppSidebar as Sidebar, type SidebarView } from "./Sidebar"
import { SidebarProvider } from "@/components/ui/sidebar"
import { ChatView } from "@/components/chat/ChatView"
import { ProjectsPanel } from "@/components/project/ProjectsPanel"
import { ApprovalsPanel } from "@/components/approvals/ApprovalsPanel"
import { apiFetch, apiFetchJson } from "@/lib/api"
import { toast } from "sonner"

interface Conversation {
  id: string
  title: string
  updated_at: string
}

export function AppShell() {
  const [activeView, setActiveView] = useState<SidebarView>("chat")
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [activeConversationId, setActiveConversationId] = useState<string | undefined>(undefined)
  const [activeProjectId, setActiveProjectId] = useState<string | undefined>(undefined)
  const [pendingApprovalsCount, setPendingApprovalsCount] = useState(0)
  const [isLoadingConversations, setIsLoadingConversations] = useState(true)

  const fetchConversations = useCallback(async () => {
    try {
      const data = (await apiFetchJson<{ items: Conversation[]; total: number }>("/conversations")) as {
        items: Conversation[]
        total: number
      }
      setConversations(
        [...data.items].sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()),
      )
    } catch (err) {
      console.error("Failed to fetch conversations:", err)
    } finally {
      setIsLoadingConversations(false)
    }
  }, [])

  const fetchPendingApprovals = useCallback(async () => {
    try {
      const data = (await apiFetchJson<{ items: { approval_id: string; status: string }[]; total: number }>(
        "/approvals?status=pending",
      )) as { items: { approval_id: string; status: string }[]; total: number }
      setPendingApprovalsCount(data.total)
    } catch {
      // non-critical
    }
  }, [])

  useEffect(() => {
    void fetchConversations()
    void fetchPendingApprovals()
    const interval = setInterval(fetchPendingApprovals, 30000)
    return () => clearInterval(interval)
  }, [fetchConversations, fetchPendingApprovals])

  // Recover from URL on mount
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const urlConversationId = params.get("conversation")
    const urlProjectId = params.get("project")
    if (urlProjectId) {
      setActiveProjectId(urlProjectId)
      setActiveView("projects")
    } else if (urlConversationId) {
      setActiveConversationId(urlConversationId)
      setActiveView("chat")
    }
  }, [])

  const handleSelectConversation = useCallback((id: string) => {
    setActiveConversationId(id)
    setActiveProjectId(undefined)
    setActiveView("chat")
    window.history.replaceState(null, "", `/?conversation=${id}`)
  }, [])

  const handleNewChat = useCallback(() => {
    setActiveConversationId(undefined)
    setActiveProjectId(undefined)
    setActiveView("chat")
    window.history.replaceState(null, "", "/")
  }, [])

  const handleDeleteConversation = useCallback(
    async (id: string) => {
      const res = await apiFetch(`/conversations/${id}`, { method: "DELETE" })
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`)
      }
      const data = (await res.json()) as { next_conversation_id?: string | null }
      setConversations((prev) => prev.filter((c) => c.id !== id))
      if (activeConversationId === id) {
        if (data.next_conversation_id) {
          handleSelectConversation(data.next_conversation_id)
        } else {
          handleNewChat()
        }
      }
      toast.success("会话已删除")
    },
    [activeConversationId, handleNewChat, handleSelectConversation],
  )

  const handleConversationCreated = useCallback((id: string, title: string) => {
    setActiveConversationId(id)
    window.history.replaceState(null, "", `/?conversation=${id}`)
    setConversations((prev) => {
      const filtered = prev.filter((c) => c.id !== id)
      return [{ id, title, updated_at: new Date().toISOString() }, ...filtered]
    })
  }, [])

  const handleOpenProject = useCallback((id: string) => {
    setActiveProjectId(id)
    setActiveView("projects")
    window.history.replaceState(null, "", `/?project=${id}`)
  }, [])

  const handleViewChange = useCallback(
    (view: SidebarView) => {
      setActiveView(view)
      if (view === "chat" && !activeConversationId) {
        window.history.replaceState(null, "", "/")
      }
    },
    [activeConversationId],
  )

  return (
    <SidebarProvider>
      <Sidebar
        activeView={activeView}
        onViewChange={handleViewChange}
        conversations={conversations}
        activeConversationId={activeConversationId}
        onSelectConversation={handleSelectConversation}
        onDeleteConversation={handleDeleteConversation}
        onNewChat={handleNewChat}
        pendingApprovalsCount={pendingApprovalsCount}
      />
      <main className="flex min-w-0 flex-1 flex-col overflow-hidden bg-background md:ml-[var(--sidebar-width)]">
        {activeView === "chat" && (
          <ChatView
            conversationId={activeConversationId}
            onConversationCreated={handleConversationCreated}
            onOpenProject={handleOpenProject}
            onOpenApprovals={() => handleViewChange("approvals")}
            isLoadingConversations={isLoadingConversations}
          />
        )}
        {activeView === "projects" && (
          <ProjectsPanel projectId={activeProjectId} onOpenProject={handleOpenProject} />
        )}
        {activeView === "approvals" && <ApprovalsPanel />}
      </main>
    </SidebarProvider>
  )
}
