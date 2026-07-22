"use client"

import { useEffect, useState } from "react"
import { FolderKanban, Plus } from "lucide-react"
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
import { apiFetchJson } from "@/lib/api"
import { toast } from "sonner"

interface Project {
  project_id: string
  title: string
  status: string
  updated_at: string
}

interface ProjectsPanelProps {
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
  if (normalized === "archived") return "已归档"
  if (normalized === "draft") return "草稿"
  return status
}

export function ProjectsPanel({ onOpenProject }: ProjectsPanelProps) {
  const [projects, setProjects] = useState<Project[]>([])
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    setIsLoading(true)
    apiFetchJson<{ items: Project[]; total: number }>("/projects")
      .then((data) => setProjects(data.items))
      .catch((err: unknown) => toast.error(err instanceof Error ? err.message : "加载项目失败"))
      .finally(() => setIsLoading(false))
  }, [])

  if (isLoading) {
    return (
      <div className="flex flex-1 items-center justify-center bg-white">
        <Spinner className="text-muted-foreground" />
      </div>
    )
  }

  return (
    <div className="flex flex-1 flex-col overflow-auto bg-white px-6 py-7">
      <div className="mb-7 flex items-center justify-between gap-4">
        <div>
          <p className="mb-2 text-sm text-[#858585]">Projects</p>
          <h1 className="text-2xl font-medium leading-8 text-[#1a1a1a]">项目工作区</h1>
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
              <EmptyDescription>项目列表会在这里展示，点击项目进入多会话工作区。</EmptyDescription>
            </EmptyHeader>
          </Empty>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {projects.map((project) => (
            <button
              key={project.project_id}
              type="button"
              className="group rounded-lg border border-[#e8e8e8] bg-white p-4 text-left transition-shadow hover:shadow-sm"
              onClick={() => onOpenProject(project.project_id)}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <h2 className="truncate text-base font-medium text-[#1a1a1a] group-hover:underline">
                    {project.title}
                  </h2>
                  <p className="mt-1 text-xs text-[#858585]">
                    更新于 {formatDate(project.updated_at)}
                  </p>
                </div>
                <Badge variant="secondary">{statusLabel(project.status)}</Badge>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
