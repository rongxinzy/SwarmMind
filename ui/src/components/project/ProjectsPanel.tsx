import { useEffect, useState } from "react"
import {
  ArrowLeft,
  CheckCircle2,
  Clock3,
  FileText,
  FolderKanban,
  Layers3,
  Plus,
} from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
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
  last_run_id?: string | null
  run_count: number
}

interface ProjectTask {
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

function formatDate(value: string) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleDateString("zh-CN", {
    month: "short",
    day: "numeric",
  })
}

function statusLabel(status: string) {
  const normalized = status.toLowerCase()
  if (normalized === "active") return "进行中"
  if (normalized === "completed") return "已完成"
  if (normalized === "blocked") return "已阻塞"
  if (normalized === "draft") return "草稿"
  return status
}

function ProjectPreview({ project, compact = false }: { project: Project; compact?: boolean }) {
  return (
    <div className="overflow-hidden rounded-lg border border-[#e8e8e8] bg-white">
      <div className={compact ? "h-36 bg-[#fafafa] p-4" : "h-56 bg-[#fafafa] p-6"}>
        <div className="mb-4 flex items-center justify-between">
          <div className="flex items-center gap-2 text-xs text-[#858585]">
            <FileText className="size-4" />
            <span>Project Brief</span>
          </div>
          <span className="rounded-full bg-white px-2 py-1 text-xs text-[#5d5d5d]">
            {statusLabel(project.status)}
          </span>
        </div>
        <div className="space-y-2">
          <div className="h-3 w-3/4 rounded-full bg-[#1a1a1a]" />
          <div className="h-2.5 w-full rounded-full bg-[#d9d9d9]" />
          <div className="h-2.5 w-5/6 rounded-full bg-[#e8e8e8]" />
          <div className="h-2.5 w-2/3 rounded-full bg-[#e8e8e8]" />
        </div>
        {!compact && (
          <div className="mt-8 grid grid-cols-3 gap-2">
            <div className="h-16 rounded-md border border-[#e8e8e8] bg-white" />
            <div className="h-16 rounded-md border border-[#e8e8e8] bg-white" />
            <div className="h-16 rounded-md border border-[#e8e8e8] bg-white" />
          </div>
        )}
      </div>
      <div className="border-t border-[#e8e8e8] p-4">
        <p className="line-clamp-2 text-sm leading-6 text-[#5d5d5d]">
          {project.objectives || "等待从会话中沉淀目标和约束。"}
        </p>
      </div>
    </div>
  )
}

export function ProjectsPanel({ projectId, onOpenProject }: ProjectsPanelProps) {
  const [projects, setProjects] = useState<Project[]>([])
  const [selected, setSelected] = useState<Project | null>(null)
  const [tasks, setTasks] = useState<ProjectTask[]>([])
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
      .catch((err: unknown) => toast.error(err instanceof Error ? err.message : "加载项目失败"))
      .finally(() => setIsLoading(false))
  }, [projectId])

  useEffect(() => {
    if (!selected) {
      setTasks([])
      return
    }
    apiFetchJson<{ items: ProjectTask[]; total: number }>(`/projects/${selected.project_id}/tasks`)
      .then((data) => setTasks(data.items))
      .catch(() => setTasks([]))
  }, [selected])

  if (isLoading) {
    return (
      <div className="flex flex-1 items-center justify-center bg-white">
        <Spinner className="text-muted-foreground" />
      </div>
    )
  }

  if (!selected) {
    return (
      <div className="flex flex-1 flex-col overflow-auto bg-white px-6 py-7">
        <div className="mb-7 flex items-center justify-between gap-4">
          <div>
            <p className="mb-2 text-sm text-[#858585]">Projects</p>
            <h1 className="text-2xl font-medium leading-8 text-[#1a1a1a]">项目交付物</h1>
          </div>
          <Button size="sm" disabled className="rounded-full">
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
                <EmptyDescription>在一次有价值的任务完成后，点击“升级为项目”即可沉淀结果。</EmptyDescription>
              </EmptyHeader>
            </Empty>
          </div>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {projects.map((project) => (
              <button
                key={project.project_id}
                type="button"
                className="group text-left outline-none"
                onClick={() => {
                  setSelected(project)
                  onOpenProject(project.project_id)
                }}
              >
                <ProjectPreview project={project} compact />
                <div className="mt-3 flex items-start justify-between gap-3 px-1">
                  <div className="min-w-0">
                    <h2 className="truncate text-base font-medium text-[#1a1a1a] group-hover:underline">
                      {project.title}
                    </h2>
                    <p className="mt-1 text-xs text-[#858585]">
                      更新于 {formatDate(project.updated_at)}
                    </p>
                  </div>
                  <div className="flex shrink-0 gap-1">
                    <Badge variant="secondary">{statusLabel(project.status)}</Badge>
                  </div>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="flex flex-1 flex-col overflow-auto bg-white px-6 py-6">
      <div className="mb-6 flex items-start justify-between gap-4">
        <div className="min-w-0">
          <Button
            variant="ghost"
            size="sm"
            className="mb-3 rounded-full px-2 text-[#5d5d5d]"
            onClick={() => {
              setSelected(null)
              window.history.replaceState(null, "", "/")
            }}
          >
            <ArrowLeft className="size-4" />
            返回项目
          </Button>
          <h1 className="text-2xl font-medium leading-8 text-[#1a1a1a]">{selected.title}</h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-[#5d5d5d]">
            {selected.objectives || "这个项目来自一次会话，正在等待补充目标、范围和下一步。"}
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <Badge variant="secondary">{statusLabel(selected.status)}</Badge>
        </div>
      </div>

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_320px]">
        <section>
          <div className="mb-3 flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-[#1a1a1a]">交付物预览</p>
              <p className="mt-1 text-xs text-[#858585]">当前以项目 seed 和运行记录生成预览。</p>
            </div>
            <Button variant="outline" size="sm" className="rounded-full" disabled>
              打开制品
            </Button>
          </div>
          <ProjectPreview project={selected} />

          <div className="mt-5 rounded-lg border border-[#e8e8e8] bg-white p-4">
            <div className="mb-4 flex items-center gap-2">
              <Layers3 className="size-4 text-[#858585]" />
              <h2 className="text-sm font-medium text-[#1a1a1a]">执行记录</h2>
            </div>
            {tasks.length === 0 ? (
              <div className="rounded-md border border-dashed border-[#d9d9d9] bg-[#fafafa] px-4 py-8 text-center">
                <p className="text-sm text-[#5d5d5d]">暂无项目任务</p>
                <p className="mt-1 text-xs text-[#858585]">后续运行会在这里形成可追踪记录。</p>
              </div>
            ) : (
              <div className="flex flex-col gap-2">
                {tasks.map((task) => (
                  <Task key={task.id}>
                    <TaskTrigger title={task.description} />
                    <TaskContent>
                      <div className="flex items-center justify-between pt-2 text-sm">
                        <span className="text-muted-foreground">创建于 {formatDate(task.created_at)}</span>
                        <Badge variant="secondary">{statusLabel(task.status)}</Badge>
                      </div>
                    </TaskContent>
                  </Task>
                ))}
              </div>
            )}
          </div>
        </section>

        <aside className="space-y-4">
          <div className="rounded-lg border border-[#e8e8e8] bg-white p-4">
            <div className="mb-3 flex items-center gap-2">
              <CheckCircle2 className="size-4 text-[#168a4a]" />
              <h2 className="text-sm font-medium text-[#1a1a1a]">下一步</h2>
            </div>
            <p className="whitespace-pre-wrap text-sm leading-6 text-[#5d5d5d]">
              {selected.stages || "从源会话继续补齐范围、约束和首个可交付结果。"}
            </p>
          </div>

          <div className="rounded-lg border border-[#e8e8e8] bg-white p-4">
            <div className="mb-3 flex items-center gap-2">
              <Clock3 className="size-4 text-[#858585]" />
              <h2 className="text-sm font-medium text-[#1a1a1a]">项目记忆</h2>
            </div>
            <dl className="space-y-3 text-sm">
              <div>
                <dt className="text-xs text-[#858585]">来源会话</dt>
                <dd className="mt-1 truncate text-[#5d5d5d]">
                  {selected.conversation_id ?? "未关联"}
                </dd>
              </div>
              <div>
                <dt className="text-xs text-[#858585]">运行次数</dt>
                <dd className="mt-1 text-[#5d5d5d]">{selected.run_count}</dd>
              </div>
              <div>
                <dt className="text-xs text-[#858585]">最近更新</dt>
                <dd className="mt-1 text-[#5d5d5d]">{formatDate(selected.updated_at)}</dd>
              </div>
            </dl>
          </div>

        </aside>
      </div>
    </div>
  )
}
