"use client"

import type { LucideIcon } from "lucide-react"
import {
  Code2Icon,
  DownloadIcon,
  EyeIcon,
  FileArchive,
  FileIcon,
  FileMusic,
  FileTextIcon,
  FileVideoCamera,
  ImageIcon,
  PackageIcon,
  Presentation,
  Table2Icon,
} from "lucide-react"

import { buttonVariants } from "@/components/ui/button"
import {
  Card,
  CardAction,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  downloadArtifactBlobUrl,
  openArtifactBlobUrl,
} from "@/core/deerflow/artifact-actions"
import {
  type ArtifactMetadata,
  type ArtifactMetadataIndex,
  artifactDisplayPath,
  artifactMetadataForPath,
  artifactUrl,
  isActiveContentArtifactPath,
  isSkillArtifactPath,
  isVirtualArtifactPath,
  resolveArtifactReference,
  skillArtifactPreviewPath,
} from "@/core/deerflow/artifacts"
import { cn } from "@/lib/utils"
import { toast } from "sonner"

export function ArtifactFileList({
  className,
  conversationId,
  files,
  artifactMetadataByPath,
  onSelect,
}: {
  className?: string
  conversationId?: string
  files: string[]
  artifactMetadataByPath?: ArtifactMetadataIndex
  onSelect?: (file: string) => void
}) {
  if (files.length === 0) {
    return null
  }

  return (
    <ul className={cn("flex w-full flex-col gap-3", className)}>
      {files.map((file) => {
        const inlineWriteFile = isWriteFileLike(file)
        const actionFile = skillArtifactPreviewPath(file) ?? file
        const url = conversationId && !inlineWriteFile ? artifactUrl(conversationId, actionFile, false) : undefined
        const downloadUrl = conversationId && !inlineWriteFile ? artifactUrl(conversationId, actionFile, true) : undefined
        const interactive = onSelect !== undefined
        const meta = artifactFileMeta(file)
        const artifactMetadata = artifactMetadataForPath(artifactMetadataByPath, file)
        const metadataParts = artifactMetadataParts(artifactMetadata)
        const canOpen = Boolean(url && !isActiveContentArtifactPath(file))
        return (
          <Card
            key={file}
            className={cn(
              "group rounded-[10px] border-[#e8e8e4] bg-white p-3 shadow-[0_1px_2px_rgba(0,0,0,0.025)]",
              interactive && "cursor-pointer transition-colors hover:border-[#d8d8d2] hover:bg-[#fbfbfa]",
            )}
            onClick={() => onSelect?.(file)}
          >
            <CardHeader className="grid-cols-[minmax(0,1fr)_auto] items-center gap-x-3 gap-y-1 px-0 py-0">
              <CardTitle className="relative min-w-0 pl-9 text-sm font-medium leading-tight text-[#1f1f1d] [overflow-wrap:anywhere]">
                <span className={cn("absolute left-0 top-0 inline-flex size-6 items-center justify-center rounded-md border", meta.iconClassName)}>
                  <meta.icon className="size-3.5" />
                </span>
                {interactive ? (
                  <span>{fileName(file)}</span>
                ) : url && canOpen ? (
                  <button
                    className="text-left hover:underline"
                    type="button"
                    onClick={(event) => {
                      event.stopPropagation()
                      void openArtifactBlobUrl(url).catch((err: unknown) => {
                        toast.error(err instanceof Error ? err.message : "Unable to open artifact")
                      })
                    }}
                  >
                    {fileName(file)}
                  </button>
                ) : (
                  fileName(file)
                )}
              </CardTitle>
              <CardDescription className="flex min-w-0 flex-wrap items-center gap-x-1.5 gap-y-1 pl-9 text-[11px] text-[#8a8a86]">
                <span className="min-w-0 truncate">{meta.label}</span>
                {metadataParts.map((part) => (
                  <span
                    key={part}
                    className="inline-flex max-w-full items-center rounded-full border border-[#ecece8] bg-[#fbfbfa] px-1.5 py-0.5 text-[10px] font-medium leading-none text-[#777770]"
                  >
                    <span className="truncate">{part}</span>
                  </span>
                ))}
              </CardDescription>
              <CardAction className="row-span-2 self-center">
                {downloadUrl && (
                  <div className="flex items-center gap-1">
                    {interactive && (
                      <button
                        aria-label="Preview artifact"
                        className={buttonVariants({
                          variant: "ghost",
                          size: "icon-sm",
                          className: "bg-[#111111] text-white shadow-[0_2px_8px_rgba(0,0,0,0.12)] hover:bg-[#242424] hover:text-white",
                        })}
                        title="Preview"
                        type="button"
                        onClick={(event) => {
                          event.stopPropagation()
                          onSelect?.(file)
                        }}
                      >
                        <EyeIcon className="size-4" />
                      </button>
                    )}
                    <button
                      aria-label="Download artifact"
                      className={buttonVariants({
                        variant: "ghost",
                        size: "icon-sm",
                        className: "text-muted-foreground opacity-70 hover:opacity-100",
                      })}
                      title="Download"
                      type="button"
                      onClick={(event) => {
                        event.stopPropagation()
                        void downloadArtifactBlobUrl(downloadUrl, fileName(actionFile)).catch((err: unknown) => {
                          toast.error(err instanceof Error ? err.message : "Unable to download artifact")
                        })
                      }}
                    >
                      <DownloadIcon className="size-4" />
                    </button>
                  </div>
                )}
              </CardAction>
            </CardHeader>
          </Card>
        )
      })}
    </ul>
  )
}

export { artifactUrl, isVirtualArtifactPath, resolveArtifactReference }

export function fileName(path: string) {
  const displayPath = artifactDisplayPath(path)
  return displayPath.split("/").filter(Boolean).pop() ?? displayPath
}

export function fileExtension(path: string) {
  const name = fileName(path)
  const ext = name.split(".").pop()
  return ext && ext !== name ? ext.toUpperCase() : "FILE"
}

export function artifactFileTypeLabel(path: string) {
  return artifactFileMeta(path).label
}

export function artifactMetadataLine(artifact: ArtifactMetadata | undefined) {
  return artifactMetadataParts(artifact).join(" · ")
}

export function artifactMetadataParts(artifact: ArtifactMetadata | undefined) {
  if (!artifact) {
    return []
  }
  const authorRole = artifact.author_role?.trim()
  return [
    formatBytes(artifact.size_bytes),
    formatArtifactType(artifact.artifact_type),
    authorRole,
  ].filter((part): part is string => Boolean(part))
}

export function ArtifactFileIcon({
  className,
  file,
}: {
  className?: string
  file: string
}) {
  const meta = artifactFileMeta(file)
  return <meta.icon className={cn("size-3.5", className)} />
}

function artifactFileMeta(path: string): {
  icon: LucideIcon
  iconClassName: string
  label: string
} {
  const ext = fileExtension(path).toLowerCase()
  if (["gif", "jpeg", "jpg", "png", "svg", "webp"].includes(ext)) {
    return {
      icon: ImageIcon,
      iconClassName: "border-[#dedede] bg-[#f7f7f5] text-[#373737]",
      label: `${fileExtension(path)} image preview`,
    }
  }
  if (ext === "csv") {
    return {
      icon: Table2Icon,
      iconClassName: "border-[#dedede] bg-[#f7f7f5] text-[#373737]",
      label: "CSV table preview",
    }
  }
  if (ext === "pdf") {
    return {
      icon: FileTextIcon,
      iconClassName: "border-[#dedede] bg-[#f7f7f5] text-[#373737]",
      label: "PDF document preview",
    }
  }
  if (["mov", "mp4", "webm"].includes(ext)) {
    return {
      icon: FileVideoCamera,
      iconClassName: "border-[#dedede] bg-[#f7f7f5] text-[#373737]",
      label: `${fileExtension(path)} video preview`,
    }
  }
  if (["aac", "flac", "m4a", "mp3", "ogg", "wav"].includes(ext)) {
    return {
      icon: FileMusic,
      iconClassName: "border-[#dedede] bg-[#f7f7f5] text-[#373737]",
      label: `${fileExtension(path)} audio preview`,
    }
  }
  if (["ppt", "pptx", "key"].includes(ext)) {
    return {
      icon: Presentation,
      iconClassName: "border-[#e8e8e8] bg-[#fafafa] text-muted-foreground",
      label: `${fileExtension(path)} presentation artifact`,
    }
  }
  if (["zip", "tar", "gz", "tgz"].includes(ext)) {
    return {
      icon: FileArchive,
      iconClassName: "border-[#e8e8e8] bg-[#fafafa] text-muted-foreground",
      label: `${fileExtension(path)} archive artifact`,
    }
  }
  if (isSkillArtifactPath(path)) {
    return {
      icon: PackageIcon,
      iconClassName: "border-[#dedede] bg-[#f7f7f5] text-[#373737]",
      label: "Skill package preview",
    }
  }
  if (ext === "md") {
    return {
      icon: FileTextIcon,
      iconClassName: "border-[#dedede] bg-[#f7f7f5] text-[#373737]",
      label: "Markdown preview",
    }
  }
  if (["css", "html", "js", "json", "jsx", "py", "sh", "sql", "ts", "tsx", "xml", "yaml", "yml"].includes(ext)) {
    return {
      icon: Code2Icon,
      iconClassName: "border-[#dedede] bg-[#f7f7f5] text-[#373737]",
      label: `${fileExtension(path)} code artifact`,
    }
  }
  return {
    icon: FileIcon,
    iconClassName: "border-[#e8e8e8] bg-[#fafafa] text-muted-foreground",
    label: `${fileExtension(path)} artifact`,
  }
}

function isWriteFileLike(path: string) {
  return path.startsWith("write-file:")
}

function formatBytes(size: number | null | undefined) {
  if (typeof size !== "number" || !Number.isFinite(size) || size < 0) {
    return null
  }
  if (size < 1024) {
    return `${size} B`
  }
  const units = ["KB", "MB", "GB"]
  let value = size / 1024
  let unitIndex = 0
  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024
    unitIndex += 1
  }
  return `${value >= 10 ? value.toFixed(0) : value.toFixed(1)} ${units[unitIndex]}`
}

function formatArtifactType(type: string | null | undefined) {
  switch (type) {
    case "write_file":
      return "generated"
    case "edit_file":
      return "edited"
    case "present_files":
      return "presented"
    case "upload":
      return "upload"
    default:
      return null
  }
}
