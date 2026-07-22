import { useCallback, useEffect, useState } from "react"
import { AppSidebar, type AppMode, type WorkView } from "./Sidebar"
import { SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar"
import { ChatView } from "@/components/chat/ChatView"
import { ProjectsPanel } from "@/components/project/ProjectsPanel"
import { ProvidersPanel } from "@/components/admin/ProvidersPanel"
import { apiFetch, apiFetchJson } from "@/lib/api"
import { toast } from "sonner"

interface Conversation {
  id: string
  title: string
  updated_at: string
}

interface Project {
  project_id: string
  title: string
}

export function AppShell() {
  const [mode, setMode] = useState<AppMode>("work")
  const [workView, setWorkView] = useState<WorkView>("tasks")
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [projects, setProjects] = useState<Project[]>([])
  const [activeConversationId, setActiveConversationId] = useState<string | undefined>(undefined)
  const [activeProjectId, setActiveProjectId] = useState<string | undefined>(undefined)
  const [isLoadingConversations, setIsLoadingConversations] = useState(true)
  const [showAdmin, setShowAdmin] = useState(false)

  const fetchConversations = useCallback(async () => {
    try {
      const data = (await apiFetchJson<{ items: Conversation[]; total: number }>("/conversations"))
      setConversations(
        [...data.items].sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()),
      )
    } catch (err) {
      console.error("Failed to fetch conversations:", err)
    } finally {
      setIsLoadingConversations(false)
    }
  }, [])

  const fetchProjects = useCallback(async () => {
    try {
      const data = await apiFetchJson<{ items: Project[]; total: number }>("/projects")
      setProjects(data.items)
    } catch (err) {
      console.error("Failed to fetch projects:", err)
    }
  }, [])

  useEffect(() => {
    void fetchConversations()
    void fetchProjects()
  }, [fetchConversations, fetchProjects])

  // Recover from URL on mount
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const urlConversationId = params.get("conversation")
    const urlProjectId = params.get("project")
    const urlView = params.get("view")
    if (urlView === "providers") {
      setShowAdmin(true)
    } else if (urlProjectId) {
      setActiveProjectId(urlProjectId)
      setWorkView("projects")
      setMode("work")
    } else if (urlConversationId) {
      setActiveConversationId(urlConversationId)
      setWorkView("tasks")
      setMode("work")
    }
  }, [])

  const handleSelectConversation = useCallback((id: string) => {
    setActiveConversationId(id)
    setActiveProjectId(undefined)
    setWorkView("tasks")
    setMode("work")
    setShowAdmin(false)
    window.history.replaceState(null, "", `/?conversation=${id}`)
  }, [])

  const handleNewChat = useCallback(() => {
    setActiveConversationId(undefined)
    setActiveProjectId(undefined)
    setMode("chat")
    setShowAdmin(false)
    window.history.replaceState(null, "", "/")
  }, [])

  const handleNewTask = useCallback(() => {
    setActiveConversationId(undefined)
    setActiveProjectId(undefined)
    setMode("work")
    setWorkView("tasks")
    setShowAdmin(false)
    window.history.replaceState(null, "", "/")
  }, [])

  const handleNewProject = useCallback(() => {
    toast.info("新建项目功能将在后续版本提供")
  }, [])

  const handleSelectProject = useCallback((id: string) => {
    setActiveProjectId(id)
    setActiveConversationId(undefined)
    setWorkView("projects")
    setMode("work")
    setShowAdmin(false)
    window.history.replaceState(null, "", `/?project=${id}`)
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
          handleNewTask()
        }
      }
      toast.success("会话已删除")
    },
    [activeConversationId, handleNewTask, handleSelectConversation],
  )

  const handleConversationCreated = useCallback((id: string, title: string) => {
    setActiveConversationId(id)
    setWorkView("tasks")
    setMode("work")
    setShowAdmin(false)
    window.history.replaceState(null, "", `/?conversation=${id}`)
    setConversations((prev) => {
      const filtered = prev.filter((c) => c.id !== id)
      return [{ id, title, updated_at: new Date().toISOString() }, ...filtered]
    })
  }, [])

  const handleOpenAdmin = useCallback(() => {
    setShowAdmin(true)
    window.history.replaceState(null, "", "/?view=providers")
  }, [])

  const handleModeChange = useCallback((next: AppMode) => {
    setMode(next)
    if (next === "work") {
      setActiveConversationId(undefined)
      setActiveProjectId(undefined)
      setWorkView("tasks")
      window.history.replaceState(null, "", "/")
    } else {
      setActiveConversationId(undefined)
      setActiveProjectId(undefined)
      window.history.replaceState(null, "", "/")
    }
  }, [])

  return (
    <SidebarProvider defaultOpen>
      <AppSidebar
        mode={mode}
        workView={workView}
        onModeChange={handleModeChange}
        onWorkViewChange={setWorkView}
        conversations={conversations}
        projects={projects}
        activeConversationId={activeConversationId}
        activeProjectId={activeProjectId}
        onSelectConversation={handleSelectConversation}
        onDeleteConversation={handleDeleteConversation}
        onSelectProject={handleSelectProject}
        onNewChat={handleNewChat}
        onNewTask={handleNewTask}
        onNewProject={handleNewProject}
        onOpenAdmin={handleOpenAdmin}
      />
      <main className="relative flex min-w-0 flex-1 flex-col overflow-hidden bg-background">
        <div className="absolute left-3 top-3 z-20 md:hidden">
          <SidebarTrigger className="size-9 rounded-full border border-[#e8e8e8] bg-white shadow-sm" />
        </div>
        {showAdmin ? (
          <ProvidersPanel />
        ) : mode === "chat" ? (
          <ChatPlaceholder />
        ) : workView === "tasks" ? (
          <ChatView
            conversationId={activeConversationId}
            onConversationCreated={handleConversationCreated}
            isLoadingConversations={isLoadingConversations}
          />
        ) : (
          <ProjectsPanel projectId={activeProjectId} onOpenProject={handleSelectProject} />
        )}
      </main>
    </SidebarProvider>
  )
}

function ChatPlaceholder() {
  return (
    <div className="flex flex-1 flex-col items-center justify-center bg-[#fbfbfa] px-6 text-center">
      <div className="max-w-md">
        <h1 className="text-2xl font-medium text-[#1a1a1a]">Chat mode placeholder</h1>
        <p className="mt-3 text-sm leading-6 text-[#5d5d5d]">
          Chat 直连模型功能将在 M1 接入。当前可先通过 Work 模式使用任务会话。
        </p>
      </div>
    </div>
  )
}
