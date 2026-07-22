"use client"

import { useCallback, useEffect, useState } from "react"
import {
  ArrowLeft,
  FileText,
  FolderKanban,
  Layers3,
  MessageSquareText,
  Plus,
  Trash2,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Spinner } from "@/components/ui/spinner"
import { ChatView } from "@/components/chat/ChatView"
import { apiFetch, apiFetchJson } from "@/lib/api"
import { toast } from "sonner"
import { cn } from "@/lib/utils"

interface Project {
  project_id: string
  title: string
  goal?: string | null
  status: string
  updated_at: string
}

interface Conversation {
  id: string
  title: string
  updated_at: string
}

interface MemoryEntry {
  key: string
  value: string
  updated_at: string
}

interface ProjectFile {
  artifact_id: string
  name?: string | null
  path?: string | null
  mime_type?: string | null
  size_bytes?: number | null
}

interface ProjectWorkspaceProps {
  projectId: string
  onBack: () => void
}

export function ProjectWorkspace({ projectId, onBack }: ProjectWorkspaceProps) {
  const [project, setProject] = useState<Project | null>(null)
  const [sessions, setSessions] = useState<Conversation[]>([])
  const [selectedSessionId, setSelectedSessionId] = useState<string | undefined>(undefined)
  const [memory, setMemory] = useState<MemoryEntry[]>([])
  const [files, setFiles] = useState<ProjectFile[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [newKey, setNewKey] = useState("")
  const [newValue, setNewValue] = useState("")

  const fetchProject = useCallback(async () => {
    try {
      const data = await apiFetchJson<Project>(`/projects/${projectId}`)
      setProject(data)
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "加载项目失败")
    }
  }, [projectId])

  const fetchSessions = useCallback(async () => {
    try {
      const data = await apiFetchJson<{ items: Conversation[] }>(`/projects/${projectId}/conversations`)
      setSessions(data.items)
    } catch (err) {
      console.error("Failed to fetch sessions:", err)
    }
  }, [projectId])

  const fetchMemory = useCallback(async () => {
    try {
      const data = await apiFetchJson<{ items: MemoryEntry[] }>(`/projects/${projectId}/memory`)
      setMemory(data.items)
    } catch (err) {
      console.error("Failed to fetch memory:", err)
    }
  }, [projectId])

  const fetchFiles = useCallback(async () => {
    try {
      const data = await apiFetchJson<{ files: ProjectFile[] }>(`/projects/${projectId}/files`)
      setFiles(data.files)
    } catch (err) {
      console.error("Failed to fetch files:", err)
    }
  }, [projectId])

  useEffect(() => {
    setIsLoading(true)
    void Promise.all([fetchProject(), fetchSessions(), fetchMemory(), fetchFiles()]).finally(() =>
      setIsLoading(false),
    )
  }, [fetchProject, fetchSessions, fetchMemory, fetchFiles])

  useEffect(() => {
    const interval = setInterval(() => {
      void fetchSessions()
      void fetchFiles()
    }, 5000)
    return () => clearInterval(interval)
  }, [fetchSessions, fetchFiles])

  const handleCreateSession = useCallback(async () => {
    try {
      const data = await apiFetchJson<Conversation>(`/projects/${projectId}/conversations`, {
        method: "POST",
      })
      setSessions((prev) => [data, ...prev])
      setSelectedSessionId(data.id)
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "创建会话失败")
    }
  }, [projectId])

  const handleSetMemory = useCallback(async () => {
    const key = newKey.trim()
    const value = newValue.trim()
    if (!key) {
      toast.error("请输入记忆键名")
      return
    }
    try {
      await apiFetchJson(`/projects/${projectId}/memory/${encodeURIComponent(key)}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ value }),
      })
      setNewKey("")
      setNewValue("")
      void fetchMemory()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "保存记忆失败")
    }
  }, [projectId, newKey, newValue, fetchMemory])

  const handleDeleteMemory = useCallback(
    async (key: string) => {
      try {
        await apiFetch(`/projects/${projectId}/memory/${encodeURIComponent(key)}`, { method: "DELETE" })
        void fetchMemory()
      } catch (err) {
        toast.error(err instanceof Error ? err.message : "删除记忆失败")
      }
    },
    [projectId, fetchMemory],
  )

  const handleSessionTitleUpdate = useCallback((id: string, title: string) => {
    setSessions((prev) =>
      prev.map((s) => (s.id === id ? { ...s, title } : s)).sort(
        (a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime(),
      ),
    )
  }, [])

  if (isLoading || !project) {
    return (
      <div className="flex flex-1 items-center justify-center bg-white">
        <Spinner className="text-muted-foreground" />
      </div>
    )
  }

  return (
    <div className="flex flex-1 overflow-hidden bg-white">
      {/* Sessions sidebar */}
      <aside className="flex w-64 flex-col border-r border-[#e8e8e8]">
        <div className="border-b border-[#e8e8e8] p-4">
          <Button
            variant="ghost"
            size="sm"
            className="mb-3 rounded-full px-2 text-[#5d5d5d]"
            onClick={onBack}
          >
            <ArrowLeft className="size-4" />
            返回项目
          </Button>
          <h2 className="truncate text-base font-medium text-[#1a1a1a]">{project.title}</h2>
          <p className="mt-1 line-clamp-2 text-xs text-[#858585]">
            {project.goal || "Project workspace"}
          </p>
        </div>
        <div className="p-3">
          <Button
            size="sm"
            className="w-full rounded-full"
            onClick={() => void handleCreateSession()}
          >
            <Plus className="size-4" />
            新任务会话
          </Button>
        </div>
        <ScrollArea className="flex-1">
          <div className="space-y-1 p-3">
            {sessions.length === 0 ? (
              <p className="px-2 py-4 text-center text-xs text-[#858585]">暂无任务会话</p>
            ) : (
              sessions.map((session) => (
                <button
                  key={session.id}
                  type="button"
                  onClick={() => setSelectedSessionId(session.id)}
                  className={cn(
                    "flex w-full items-center gap-2 rounded-lg px-2 py-2 text-left text-sm transition-colors",
                    selectedSessionId === session.id
                      ? "bg-[#f4f4f4] text-[#1a1a1a]"
                      : "text-[#5d5d5d] hover:bg-[#f9f9f9]",
                  )}
                >
                  <MessageSquareText className="size-4 shrink-0" />
                  <span className="truncate">{session.title}</span>
                </button>
              ))
            )}
          </div>
        </ScrollArea>
      </aside>

      {/* Main chat area */}
      <main className="flex min-w-0 flex-1 flex-col">
        {selectedSessionId ? (
          <ChatView
            conversationId={selectedSessionId}
            onConversationCreated={(id, title) => handleSessionTitleUpdate(id, title)}
            isLoadingConversations={false}
          />
        ) : (
          <div className="flex flex-1 flex-col items-center justify-center bg-[#fbfbfa] px-6 text-center">
            <div className="max-w-md">
              <FolderKanban className="mx-auto size-10 text-[#d9d9d9]" />
              <h1 className="mt-4 text-xl font-medium text-[#1a1a1a]">选择一个任务会话开始</h1>
              <p className="mt-2 text-sm text-[#5d5d5d]">
                左侧会列出项目中的所有任务会话，也可以新建一个会话。
              </p>
            </div>
          </div>
        )}
      </main>

      {/* Right info sidebar */}
      <aside className="flex w-72 flex-col border-l border-[#e8e8e8]">
        <ScrollArea className="flex-1 p-4">
          <div className="mb-6">
            <div className="mb-3 flex items-center gap-2">
              <Layers3 className="size-4 text-[#858585]" />
              <h3 className="text-sm font-medium text-[#1a1a1a]">项目记忆</h3>
            </div>
            <div className="space-y-2">
              <Input
                placeholder="键名"
                value={newKey}
                onChange={(e) => setNewKey(e.target.value)}
                className="h-8 text-xs"
              />
              <Input
                placeholder="值"
                value={newValue}
                onChange={(e) => setNewValue(e.target.value)}
                className="h-8 text-xs"
              />
              <Button
                size="sm"
                variant="outline"
                className="w-full text-xs"
                onClick={() => void handleSetMemory()}
              >
                保存记忆
              </Button>
            </div>
            {memory.length > 0 && (
              <div className="mt-3 space-y-2">
                {memory.map((entry) => (
                  <div
                    key={entry.key}
                    className="rounded-md border border-[#e8e8e8] bg-[#fafafa] p-2"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-xs font-medium text-[#1a1a1a]">{entry.key}</span>
                      <button
                        type="button"
                        onClick={() => void handleDeleteMemory(entry.key)}
                        className="text-[#858585] hover:text-red-600"
                        aria-label="删除"
                      >
                        <Trash2 className="size-3" />
                      </button>
                    </div>
                    <p className="mt-1 whitespace-pre-wrap text-xs text-[#5d5d5d]">{entry.value}</p>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div>
            <div className="mb-3 flex items-center gap-2">
              <FileText className="size-4 text-[#858585]" />
              <h3 className="text-sm font-medium text-[#1a1a1a]">项目文件</h3>
            </div>
            {files.length === 0 ? (
              <p className="text-xs text-[#858585]">暂无文件</p>
            ) : (
              <div className="space-y-2">
                {files.map((file) => (
                  <div
                    key={file.artifact_id}
                    className="flex items-center gap-2 rounded-md border border-[#e8e8e8] p-2"
                  >
                    <FileText className="size-4 shrink-0 text-[#858585]" />
                    <span className="truncate text-xs text-[#5d5d5d]">
                      {file.name || file.path || file.artifact_id}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </ScrollArea>
      </aside>
    </div>
  )
}
