import { useEffect, useState } from "react"
import { FolderKanban, Plus } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty"
import { Spinner } from "@/components/ui/spinner"
import { Task, TaskContent, TaskTrigger } from "@/components/ai-elements/task"
import { apiFetchJson } from "@/lib/api"
import { toast } from "sonner"

interface Project {
  project_id: string
  title: string
  status: string
  objectives: string
  stages: string
  created_at: string
  updated_at: string
  conversation_id?: string | null
  pending_approvals_count: number
  last_run_id?: string | null
  run_count: number
}

interface Task {
  id: string
  description: string
  status: string
  run_id: string
  created_at: string
  completed_at?: string | null
}

interface ProjectsPanelProps {
  projectId?: string
  onOpenProject: (id: string) => void
}

export function ProjectsPanel({ projectId, onOpenProject }: ProjectsPanelProps) {
  const [projects, setProjects] = useState<Project[]>([])
  const [selected, setSelected] = useState<Project | null>(null)
  const [tasks, setTasks] = useState<Task[]>([])
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    setIsLoading(true)
    apiFetchJson<{ items: Project[]; total: number }>("/projects")
      .then((data) => {
        setProjects(data.items)
        if (projectId) {
          const found = data.items.find((p) => p.project_id === projectId)
          if (found) setSelected(found)
        }
      })
      .catch((err) => toast.error(err instanceof Error ? err.message : "加载项目失败"))
      .finally(() => setIsLoading(false))
  }, [projectId])

  useEffect(() => {
    if (!selected) {
      setTasks([])
      return
    }
    apiFetchJson<{ items: Task[]; total: number }>(`/projects/${selected.project_id}/tasks`)
      .then((data) => setTasks(data.items))
      .catch(() => setTasks([]))
  }, [selected])

  if (isLoading) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <Spinner className="text-muted-foreground" />
      </div>
    )
  }

  if (!selected) {
    return (
      <div className="flex flex-1 flex-col overflow-auto p-6">
        <div className="mb-4 flex items-center justify-between">
          <h1 className="text-xl font-semibold">项目</h1>
          <Button size="sm" disabled>
            <Plus data-icon="inline-start" />
            新建项目
          </Button>
        </div>
        {projects.length === 0 ? (
          <div className="flex flex-1 flex-col items-center justify-center">
            <Empty className="max-w-md">
              <EmptyHeader>
                <EmptyMedia variant="icon">
                  <FolderKanban />
                </EmptyMedia>
                <EmptyTitle>暂无项目</EmptyTitle>
                <EmptyDescription>在聊天中点击“升级为项目”即可创建。</EmptyDescription>
              </EmptyHeader>
            </Empty>
          </div>
        ) : (
          <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
            {projects.map((p) => (
              <Card
                key={p.project_id}
                className="cursor-pointer transition-shadow hover:shadow-md"
                onClick={() => {
                  setSelected(p)
                  onOpenProject(p.project_id)
                }}
              >
                <CardHeader>
                  <CardTitle className="text-base">{p.title}</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="line-clamp-2 text-sm text-muted-foreground">{p.objectives}</p>
                  <div className="mt-3 flex items-center gap-2">
                    <Badge variant="secondary">{p.status}</Badge>
                    {p.pending_approvals_count > 0 && (
                      <Badge variant="destructive">{p.pending_approvals_count} 待审批</Badge>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="flex flex-1 flex-col overflow-auto p-6">
      <div className="mb-4 flex items-center gap-2">
        <Button variant="ghost" size="sm" onClick={() => setSelected(null)}>
          ← 返回
        </Button>
        <h1 className="text-xl font-semibold">{selected.title}</h1>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-base">目标</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="whitespace-pre-wrap text-sm text-muted-foreground">{selected.objectives}</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">阶段</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="whitespace-pre-wrap text-sm text-muted-foreground">{selected.stages}</p>
          </CardContent>
        </Card>

        <Card className="lg:col-span-3">
          <CardHeader>
            <CardTitle className="text-base">任务</CardTitle>
          </CardHeader>
          <CardContent>
            {tasks.length === 0 ? (
              <Empty className="py-8">
                <EmptyHeader>
                  <EmptyTitle>暂无任务</EmptyTitle>
                </EmptyHeader>
              </Empty>
            ) : (
              <div className="flex flex-col gap-2">
                {tasks.map((t) => (
                  <Task key={t.id}>
                    <TaskTrigger title={t.description} />
                    <TaskContent>
                      <div className="flex items-center justify-between pt-2 text-sm">
                        <span className="text-muted-foreground">创建于 {t.created_at}</span>
                        <Badge variant="secondary">{t.status}</Badge>
                      </div>
                    </TaskContent>
                  </Task>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
