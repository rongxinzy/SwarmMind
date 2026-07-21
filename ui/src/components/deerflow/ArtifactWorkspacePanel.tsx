"use client"

import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import {
  ChevronLeftIcon,
  ChevronRightIcon,
  Code2Icon,
  CopyIcon,
  DownloadIcon,
  EyeIcon,
  ExternalLinkIcon,
  MinusIcon,
  MonitorIcon,
  PlusIcon,
  RefreshCwIcon,
  RotateCcwIcon,
  SmartphoneIcon,
  TabletIcon,
  XIcon,
} from "lucide-react"
import { toast } from "sonner"
import type { BundledLanguage } from "shiki"

import {
  Artifact,
  ArtifactAction,
  ArtifactActions,
  ArtifactContent,
  ArtifactHeader,
  ArtifactTitle,
} from "@/components/ai-elements/artifact"
import { CodeBlockContent } from "@/components/ai-elements/code-block"
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
} from "@/components/ui/select"
import { Button } from "@/components/ui/button"
import { Spinner } from "@/components/ui/spinner"
import {
  downloadArtifactBlobUrl,
  openArtifactBlobUrl,
} from "@/core/deerflow/artifact-actions"
import {
  appendHtmlPreviewBaseHref,
  appendHtmlPreviewSandboxCompatibility,
  appendHtmlPreviewScrollRestoration,
  createHtmlPreviewScrollKey,
  HTML_PREVIEW_SCROLL_MESSAGE_SOURCE,
} from "@/core/deerflow/artifact-preview"
import {
  cachedArtifactBlob,
  cachedArtifactText,
  loadCachedArtifactBlob,
  loadCachedArtifactText,
} from "@/core/deerflow/artifact-cache"
import {
  OFFICE_PREVIEW_MAX_BYTES,
  SPREADSHEET_PREVIEW_MAX_COLUMNS,
  SPREADSHEET_PREVIEW_MAX_ROWS,
  spreadsheetCellText,
  spreadsheetColumnLabel,
} from "@/core/deerflow/office-preview"
import {
  type ArtifactMetadata,
  type ArtifactMetadataIndex,
  artifactMetadataForPath,
  getWriteFileArtifactState,
  isActiveContentArtifactPath,
  isSkillArtifactPath,
  isWriteFileArtifactReference,
  parseWriteFileArtifactReference,
  skillArtifactPreviewPath,
} from "@/core/deerflow/artifacts"
import { apiFetch } from "@/lib/api"
import { cn } from "@/lib/utils"
import type { ChatMessage } from "@/types/chat"

import {
  ArtifactFileIcon,
  artifactMetadataLine,
  artifactMetadataParts,
  artifactFileTypeLabel,
  artifactUrl,
  fileExtension,
  fileName,
} from "./ArtifactFileList"
import { MarkdownContent } from "./MarkdownContent"

interface ArtifactWorkspacePanelProps {
  className?: string
  conversationId?: string
  files: string[]
  artifactMetadataByPath?: ArtifactMetadataIndex
  messages?: ChatMessage[]
  selectedFile: string | null
  onSelect: (file: string) => void
  onClose: () => void
}

const TEXT_EXTENSIONS = new Set([
  "css",
  "csv",
  "html",
  "js",
  "json",
  "jsx",
  "log",
  "md",
  "py",
  "sh",
  "sql",
  "svg",
  "ts",
  "tsx",
  "txt",
  "xml",
  "yaml",
  "yml",
])

const IMAGE_EXTENSIONS = new Set(["gif", "jpeg", "jpg", "png", "webp"])
const PDF_EXTENSIONS = new Set(["pdf"])
const DOCX_EXTENSIONS = new Set(["docx"])
const SPREADSHEET_EXTENSIONS = new Set(["xlsx"])
const PRESENTATION_EXTENSIONS = new Set(["pptx"])
const VIDEO_EXTENSIONS = new Set(["mov", "mp4", "webm"])
const AUDIO_EXTENSIONS = new Set(["aac", "flac", "m4a", "mp3", "ogg", "wav"])
const PREVIEWABLE_TEXT_EXTENSIONS = new Set(["csv", "html", "md", "svg"])
const HIGHLIGHT_MAX_CHARS = 200_000
const CSV_MAX_ROWS = 80
const CSV_MAX_COLUMNS = 12
const WRITE_FILE_PREVIEW_REFRESH_INTERVAL_MS = 3000
const PDF_ZOOM_STEPS = [0.75, 1, 1.25, 1.5, 2] as const

export function ArtifactWorkspacePanel({
  className,
  conversationId,
  files,
  artifactMetadataByPath,
  messages = [],
  selectedFile,
  onSelect,
  onClose,
}: ArtifactWorkspacePanelProps) {
  const activeFile = selectedFile ?? files[0] ?? null
  const activeExt = activeFile ? extension(activeFile) : ""
  const supportsCodePreviewToggle = PREVIEWABLE_TEXT_EXTENSIONS.has(activeExt) || isSkillArtifactPath(activeFile ?? undefined)
  const [viewMode, setViewMode] = useState<"code" | "preview">("preview")

  useEffect(() => {
    if (activeFile && !selectedFile) {
      onSelect(activeFile)
    }
  }, [activeFile, onSelect, selectedFile])

  useEffect(() => {
    setViewMode(supportsCodePreviewToggle ? "preview" : "code")
  }, [activeFile, supportsCodePreviewToggle])

  if (!conversationId || !activeFile) {
    return null
  }
  const activeWriteFile = parseWriteFileArtifactReference(activeFile)
  const activeStoredFile = activeWriteFile?.path ?? activeFile
  const activeActionFile = skillArtifactPreviewPath(activeStoredFile) ?? activeStoredFile
  const activeFileIndex = Math.max(files.findIndex((file) => file === activeFile), 0)
  const activeMetadata = artifactMetadataForPath(artifactMetadataByPath, activeFile)
  const activeContext = artifactContext(activeFile, activeFileIndex, files.length, activeMetadata)
  const activeMetadataParts = artifactMetadataParts(activeMetadata)
  const activeWriteFileState = activeWriteFile ? getWriteFileArtifactState(messages, activeFile) : null
  const activeInlineContent = activeWriteFileState?.content ?? null
  const activeArtifactUrl = artifactUrl(conversationId, activeActionFile, false)
  const activeArtifactDownloadUrl = artifactUrl(conversationId, activeActionFile, true)
  const canOpenActiveArtifact = !isActiveContentArtifactPath(activeStoredFile)

  const copyInlineArtifact = async () => {
    if (activeInlineContent === null) {
      return
    }
    await navigator.clipboard.writeText(activeInlineContent)
    toast.success("Artifact copied")
  }

  const openActiveArtifact = async () => {
    try {
      await openArtifactBlobUrl(activeArtifactUrl)
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Unable to open artifact")
    }
  }

  const downloadActiveArtifact = async () => {
    try {
      await downloadArtifactBlobUrl(activeArtifactDownloadUrl, fileName(activeActionFile))
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Unable to download artifact")
    }
  }

  return (
    <aside className={cn("h-full min-w-0 border-l border-[#e8e8e8] bg-[#fafafa] p-3", className)}>
      <Artifact className="h-full min-h-0 rounded-lg border-[#e8e8e8] bg-white shadow-none">
        <ArtifactHeader className="shrink-0 gap-3 px-3 py-2">
          <div className="flex min-w-0 flex-1 items-start gap-2">
            <span className="mt-0.5 inline-flex size-7 shrink-0 items-center justify-center rounded-md border border-[#e8e8e4] bg-[#f7f7f5] text-[#373737]">
              <ArtifactFileIcon file={activeStoredFile} />
            </span>
            <ArtifactTitle className="min-w-0 flex-1 leading-tight">
              {activeWriteFile ? (
                <span className="block truncate px-1">{fileName(activeStoredFile)}</span>
              ) : files.length > 1 ? (
                <Select
                  value={activeFile}
                  onValueChange={(value) => {
                    if (value) {
                      onSelect(value)
                    }
                  }}
                >
                  <SelectTrigger className="h-6 max-w-full border-none bg-transparent px-0 shadow-none">
                    <span className="block min-w-0 truncate">{fileName(activeStoredFile)}</span>
                  </SelectTrigger>
                  <SelectContent align="start" className="min-w-72">
                    <SelectGroup>
                      {files.map((file) => (
                        <SelectItem key={file} value={file}>
                          {fileName(file)}
                        </SelectItem>
                      ))}
                    </SelectGroup>
                  </SelectContent>
                </Select>
              ) : (
                <span className="block truncate">{fileName(activeFile)}</span>
              )}
              <span className="mt-1 flex min-w-0 flex-wrap items-center gap-x-1.5 gap-y-1 text-[11px] font-normal text-[#8a8a86]">
                <span className="min-w-0 truncate">{activeContext.typeLabel}</span>
                {activeMetadataParts.map((part) => (
                  <span
                    key={part}
                    className="inline-flex max-w-full items-center rounded-full border border-[#ecece8] bg-[#fbfbfa] px-1.5 py-0.5 text-[10px] font-medium leading-none text-[#777770]"
                  >
                    <span className="truncate">{part}</span>
                  </span>
                ))}
                <span className="min-w-0 truncate text-[#a0a09a]">{activeContext.directory}</span>
              </span>
            </ArtifactTitle>
          </div>
          {supportsCodePreviewToggle && (
            <div className="flex shrink-0 items-center rounded-md border border-[#e8e8e8] bg-[#f8f8f7] p-0.5">
              <Button
                aria-pressed={viewMode === "code"}
                className={cn(
                  "size-7 rounded-[5px] text-[#777] hover:bg-white hover:text-[#222]",
                  viewMode === "code" && "bg-white text-[#222] shadow-[0_1px_2px_rgba(0,0,0,0.05)]",
                )}
                size="icon-sm"
                title="Code"
                type="button"
                variant="ghost"
                onClick={() => setViewMode("code")}
              >
                <Code2Icon className="size-3.5" />
              </Button>
              <Button
                aria-pressed={viewMode === "preview"}
                className={cn(
                  "size-7 rounded-[5px] text-[#777] hover:bg-white hover:text-[#222]",
                  viewMode === "preview" && "bg-white text-[#222] shadow-[0_1px_2px_rgba(0,0,0,0.05)]",
                )}
                size="icon-sm"
                title="Preview"
                type="button"
                variant="ghost"
                onClick={() => setViewMode("preview")}
              >
                <EyeIcon className="size-3.5" />
              </Button>
            </div>
          )}
          <ArtifactActions>
            {activeInlineContent !== null && (
              <ArtifactAction
                icon={CopyIcon}
                label="Copy"
                tooltip="Copy"
                onClick={() => void copyInlineArtifact()}
              />
            )}
            {!activeWriteFile && (
              <>
                {canOpenActiveArtifact && (
                  <ArtifactAction
                    icon={ExternalLinkIcon}
                    label="Open"
                    tooltip="Open in new tab"
                    onClick={() => void openActiveArtifact()}
                  />
                )}
                <ArtifactAction
                  icon={DownloadIcon}
                  label="Download"
                  tooltip="Download"
                  onClick={() => void downloadActiveArtifact()}
                />
              </>
            )}
            <ArtifactAction
              icon={XIcon}
              label="Close"
              tooltip="Close"
              onClick={onClose}
            />
          </ArtifactActions>
        </ArtifactHeader>
        <ArtifactContent className="relative min-h-0 overflow-hidden p-0">
          <div
            className={cn(
              "absolute inset-0 grid min-h-0 grid-cols-1 overflow-hidden",
              files.length > 1 && "md:grid-cols-[172px_minmax(0,1fr)]",
            )}
          >
            {files.length > 1 && (
              <ArtifactFileRail files={files} activeFile={activeFile} artifactMetadataByPath={artifactMetadataByPath} onSelect={onSelect} />
            )}
            <ArtifactPreview
              artifactMetadata={activeMetadata}
              conversationId={conversationId}
              file={activeFile}
              messages={messages}
              viewMode={viewMode}
            />
          </div>
        </ArtifactContent>
      </Artifact>
    </aside>
  )
}

function ArtifactFileRail({
  files,
  activeFile,
  artifactMetadataByPath,
  onSelect,
}: {
  files: string[]
  activeFile: string
  artifactMetadataByPath?: ArtifactMetadataIndex
  onSelect: (file: string) => void
}) {
  return (
    <nav aria-label="Artifact files" className="hidden min-h-0 flex-col border-r border-[#eeeeec] bg-[#fbfbfa] p-2 md:flex">
      <div className="mb-2 flex items-center justify-between gap-2 px-1">
        <span className="text-[11px] font-medium text-[#8a8a86]">Files</span>
        <span className="shrink-0 rounded-full border border-[#e8e8e4] bg-white px-2 py-0.5 text-[10px] font-medium text-[#777770]">
          {files.length}
        </span>
      </div>
      <div className="min-h-0 space-y-1 overflow-auto pr-1">
        {files.map((file, index) => {
          const active = file === activeFile
          const context = artifactContext(file, index, files.length, artifactMetadataForPath(artifactMetadataByPath, file))
          return (
            <button
              key={file}
              type="button"
              className={cn(
                "flex w-full items-start gap-2 rounded-md px-2 py-2 text-left text-xs text-[#5f5f5c] transition-colors hover:bg-white hover:text-[#202020]",
                active && "bg-white text-[#202020] shadow-[0_1px_2px_rgba(0,0,0,0.05)]",
              )}
              onClick={() => onSelect(file)}
            >
              <span className="mt-0.5 inline-flex size-5 shrink-0 items-center justify-center rounded border border-[#e8e8e4] bg-[#f7f7f5] text-[#5f5f5c]">
                <ArtifactFileIcon file={file} className="size-3" />
              </span>
              <span className="min-w-0 flex-1">
                <span className="block truncate font-medium">{fileName(file)}</span>
                <span className="mt-0.5 block truncate text-[10px] text-[#9b9b96]">{context.shortLabel}</span>
                <span className="mt-0.5 block truncate text-[10px] text-[#b0b0aa]">{context.directory}</span>
              </span>
            </button>
          )
        })}
      </div>
    </nav>
  )
}

function ArtifactPreview({
  artifactMetadata,
  conversationId,
  file,
  messages,
  viewMode,
}: {
  artifactMetadata?: ArtifactMetadata
  conversationId: string
  file: string
  messages: ChatMessage[]
  viewMode: "code" | "preview"
}) {
  const writeFilePath = parseWriteFileArtifactReference(file)?.path
  const isInlineWriteFile = writeFilePath !== undefined
  const displayFile = writeFilePath ?? file
  const ext = extension(displayFile)
  const contentFile = skillArtifactPreviewPath(displayFile) ?? displayFile
  const contentExt = isSkillArtifactPath(displayFile) ? "md" : ext
  const url = artifactUrl(conversationId, contentFile, false)
  const artifactCacheKey = `${conversationId}:${contentFile}:${artifactMetadata?.artifact_id ?? "unregistered"}`
  const writeFileState = useMemo(
    () => isInlineWriteFile ? getWriteFileArtifactState(messages, file) : null,
    [file, isInlineWriteFile, messages],
  )
  const inlineContent = writeFileState?.content ?? null
  const visibleInlineContent = useThrottledValue(
    inlineContent ?? "",
    writeFileState?.status === "writing" ? WRITE_FILE_PREVIEW_REFRESH_INTERVAL_MS : 0,
    file,
  )
  const [content, setContent] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const isText = TEXT_EXTENSIONS.has(contentExt)
  const isImage = IMAGE_EXTENSIONS.has(ext)
  const isPdf = PDF_EXTENSIONS.has(ext)
  const isDocx = DOCX_EXTENSIONS.has(ext)
  const isSpreadsheet = SPREADSHEET_EXTENSIONS.has(ext)
  const isPresentation = PRESENTATION_EXTENSIONS.has(ext)
  const isVideo = VIDEO_EXTENSIONS.has(ext)
  const isAudio = AUDIO_EXTENSIONS.has(ext)
  const previewMimeType = contentExt === "svg" ? "image/svg+xml" : null
  const [textObjectUrl, setTextObjectUrl] = useState<string | null>(null)
  const [blobObjectUrl, setBlobObjectUrl] = useState<string | null>(null)
  const [artifactBlob, setArtifactBlob] = useState<Blob | null>(null)

  useEffect(() => {
    if (!isText) {
      setContent(null)
      setError(null)
      setIsLoading(false)
      return
    }

    if (isInlineWriteFile) {
      if (writeFileState?.status === "failed") {
        setContent(null)
        setError("The write_file call did not complete successfully.")
        setIsLoading(false)
        return
      }
      if (writeFileState?.content === null || writeFileState === null) {
        setContent(null)
        setError("The live write_file draft is unavailable.")
        setIsLoading(false)
        return
      }
      setContent(visibleInlineContent)
      setError(null)
      setIsLoading(false)
      return
    }

    const cached = cachedArtifactText(artifactCacheKey)
    if (cached !== undefined) {
      setContent(cached)
      setError(null)
      setIsLoading(false)
      return
    }

    let cancelled = false
    setIsLoading(true)
    setError(null)
    loadCachedArtifactText(artifactCacheKey, () => fetchArtifactText(url))
      .then((text) => {
        if (!cancelled) {
          setContent(text)
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load artifact")
          setContent(null)
        }
      })
      .finally(() => {
        if (!cancelled) {
          setIsLoading(false)
        }
      })

    return () => {
      cancelled = true
    }
  }, [artifactCacheKey, isInlineWriteFile, isText, url, visibleInlineContent, writeFileState])

  useEffect(() => {
    if (!previewMimeType || viewMode !== "preview" || content === null) {
      setTextObjectUrl(null)
      return
    }

    const blobUrl = URL.createObjectURL(new Blob([content], { type: previewMimeType }))
    setTextObjectUrl(blobUrl)

    return () => {
      URL.revokeObjectURL(blobUrl)
    }
  }, [content, previewMimeType, viewMode])

  useEffect(() => {
    if (isText) {
      setBlobObjectUrl(null)
      setArtifactBlob(null)
      return
    }

    let cancelled = false
    let activeObjectUrl: string | null = null

    setBlobObjectUrl(null)
    setArtifactBlob(null)
    setIsLoading(true)
    setError(null)

    const cached = cachedArtifactBlob(artifactCacheKey)
    const blobRequest = cached ? Promise.resolve(cached) : loadCachedArtifactBlob(artifactCacheKey, () => fetchArtifactBlob(url))

    blobRequest
      .then((blob) => {
        const nextObjectUrl = URL.createObjectURL(blob)
        if (cancelled) {
          URL.revokeObjectURL(nextObjectUrl)
          return
        }
        activeObjectUrl = nextObjectUrl
        setArtifactBlob(blob)
        setBlobObjectUrl(nextObjectUrl)
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load artifact")
          setArtifactBlob(null)
          setBlobObjectUrl(null)
        }
      })
      .finally(() => {
        if (!cancelled) {
          setIsLoading(false)
        }
      })

    return () => {
      cancelled = true
      if (activeObjectUrl) {
        URL.revokeObjectURL(activeObjectUrl)
      }
    }
  }, [artifactCacheKey, isText, url])

  const copyContent = useCallback(async () => {
    if (content === null) {
      return
    }
    await navigator.clipboard.writeText(content)
    toast.success("Artifact copied")
  }, [content])

  const rendered = useMemo(() => {
    if (!isText) {
      if (isLoading) {
        return (
          <div className="flex h-full items-center justify-center">
            <Spinner className="text-muted-foreground" />
          </div>
        )
      }
      if (error) {
        return <ArtifactPreviewError error={error} />
      }
      if (!blobObjectUrl) {
        return (
          <div className="flex h-full items-center justify-center">
            <Spinner className="text-muted-foreground" />
          </div>
        )
      }
      if (isImage) {
        return (
          <div className="flex h-full items-center justify-center bg-[#f7f7f7] p-4">
            <img className="max-h-full max-w-full rounded-md object-contain" src={blobObjectUrl} alt={fileName(displayFile)} />
          </div>
        )
      }
      if (isPdf) {
        return <PdfPreview src={blobObjectUrl} title={fileName(displayFile)} />
      }
      if (isDocx && artifactBlob) {
        return <DocxPreview blob={artifactBlob} title={fileName(displayFile)} />
      }
      if (isSpreadsheet && artifactBlob) {
        return <SpreadsheetPreview blob={artifactBlob} title={fileName(displayFile)} />
      }
      if (isPresentation && artifactBlob) {
        return <PresentationPreview blob={artifactBlob} title={fileName(displayFile)} />
      }
      if (isVideo) {
        return <VideoPreview src={blobObjectUrl} title={fileName(displayFile)} />
      }
      if (isAudio) {
        return <AudioPreview src={blobObjectUrl} title={fileName(displayFile)} />
      }
      return <UnsupportedArtifactPreview filename={fileName(displayFile)} typeLabel={artifactFileTypeLabel(displayFile)} />
    }

    if (isLoading) {
      return (
        <div className="flex h-full items-center justify-center bg-[#f7f7f7] p-4">
          <Spinner className="text-muted-foreground" />
        </div>
      )
    }
    if (error) {
      return <ArtifactPreviewError error={error} />
    }
    if (viewMode === "code") {
      return <ArtifactCodeView content={content ?? ""} ext={contentExt} />
    }
    if (contentExt === "csv") {
      return <CsvPreview content={content ?? ""} />
    }
    if (contentExt === "md") {
      return (
        <div className="h-full overflow-auto p-4">
          <MarkdownContent
            conversationId={conversationId}
            content={content ?? ""}
            isLoading={false}
          />
        </div>
      )
    }
    if (contentExt === "html") {
      return (
        <HtmlArtifactPreview
          content={content ?? ""}
          scrollKey={`${conversationId}:${contentFile}`}
          url={url}
        />
      )
    }
    if (contentExt === "svg") {
      return (
        <div className="flex h-full items-center justify-center bg-[#f7f7f7] p-4">
          {textObjectUrl ? (
            <img className="max-h-full max-w-full rounded-md object-contain" src={textObjectUrl} alt={fileName(displayFile)} />
          ) : (
            <Spinner className="text-muted-foreground" />
          )}
        </div>
      )
    }
    return null

  }, [artifactBlob, blobObjectUrl, content, contentExt, contentFile, conversationId, displayFile, error, isAudio, isDocx, isImage, isLoading, isPdf, isPresentation, isSpreadsheet, isText, isVideo, textObjectUrl, url, viewMode])

  return (
    <div className="relative min-h-0 overflow-hidden">
      {isText && content !== null && !isInlineWriteFile && contentExt !== "html" && (
        <button
          type="button"
          className="absolute right-3 top-3 z-10 inline-flex size-8 items-center justify-center rounded-md border border-[#e8e8e8] bg-white text-muted-foreground shadow-sm hover:text-foreground"
          onClick={() => void copyContent()}
          aria-label="Copy artifact"
        >
          <CopyIcon className="size-4" />
        </button>
      )}
      {rendered}
    </div>
  )
}

function ArtifactPreviewError({ error }: { error: string }) {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-2 p-6 text-center text-sm text-muted-foreground">
      <p>Artifact preview unavailable.</p>
      <p>{error}</p>
    </div>
  )
}

async function fetchArtifactText(url: string) {
  return fetchArtifact(url, (response) => response.text())
}

async function fetchArtifactBlob(url: string) {
  return fetchArtifact(url, (response) => response.blob())
}

async function fetchArtifact<T>(url: string, read: (response: Response) => Promise<T>) {
  const response = await apiFetch(url)
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`)
  }
  return read(response)
}

function artifactContext(path: string, index: number, total: number, metadata: ArtifactMetadata | undefined) {
  const displayPath = parseWriteFileArtifactReference(path)?.path ?? path
  const typeLabel = artifactFileTypeLabel(displayPath)
  const directory = artifactDirectory(displayPath)
  const origin = isWriteFileArtifactReference(path) ? "Inline draft" : "Saved artifact"
  const position = total > 1 ? `${index + 1} of ${total}` : "Single file"
  const metadataLine = artifactMetadataLine(metadata)

  return {
    directory,
    typeLabel,
    shortLabel: metadataLine ? `${typeLabel} · ${metadataLine}` : typeLabel,
    summary: [typeLabel, metadataLine, origin, position, directory].filter(Boolean).join(" · "),
  }
}

function artifactDirectory(path: string) {
  const displayPath = path.replace(/^\/mnt\/user-data\/?/, "")
  const parts = displayPath.split("/").filter(Boolean)
  if (parts.length <= 1) {
    return "/"
  }
  return `/${parts.slice(0, -1).join("/")}`
}

function HtmlArtifactPreview({
  content,
  scrollKey,
  url,
}: {
  content: string
  scrollKey: string
  url: string
}) {
  const iframeRef = useRef<HTMLIFrameElement | null>(null)
  const scrollPositionRef = useRef({ x: 0, y: 0 })
  const scrollMessageKey = useMemo(() => createHtmlPreviewScrollKey(scrollKey), [scrollKey])
  const [viewport, setViewport] = useState<"desktop" | "tablet" | "mobile">("desktop")
  const [refreshRevision, setRefreshRevision] = useState(0)
  const previewContent = useMemo(
    () => appendHtmlPreviewScrollRestoration(
      appendHtmlPreviewSandboxCompatibility(appendHtmlPreviewBaseHref(content, url)),
      scrollKey,
    ),
    [content, scrollKey, url],
  )

  useEffect(() => {
    scrollPositionRef.current = { x: 0, y: 0 }
  }, [scrollMessageKey])

  useEffect(() => {
    const handleMessage = (event: MessageEvent) => {
      if (event.source !== iframeRef.current?.contentWindow) {
        return
      }
      if (!isArtifactScrollMessage(event.data, scrollMessageKey)) {
        return
      }

      if (event.data.type === "save") {
        const x = scrollCoordinate(event.data.x)
        const y = scrollCoordinate(event.data.y)
        if (x !== undefined && y !== undefined) {
          scrollPositionRef.current = { x, y }
        }
        return
      }

      iframeRef.current?.contentWindow?.postMessage(
        {
          source: HTML_PREVIEW_SCROLL_MESSAGE_SOURCE,
          key: scrollMessageKey,
          type: "restore",
          ...scrollPositionRef.current,
        },
        "*",
      )
    }

    window.addEventListener("message", handleMessage)
    return () => window.removeEventListener("message", handleMessage)
  }, [scrollMessageKey])

  return (
    <div className="grid size-full min-h-0 grid-rows-[40px_minmax(0,1fr)] bg-[#f5f5f3]">
      <div className="flex items-center justify-between gap-2 border-b border-[#e5e5e1] bg-white px-2">
        <div
          aria-label="HTML preview viewport"
          className="flex items-center rounded-md border border-[#e4e4df] bg-[#f8f8f6] p-0.5"
          role="group"
        >
          {([
            ["desktop", MonitorIcon, "Desktop preview"],
            ["tablet", TabletIcon, "Tablet preview"],
            ["mobile", SmartphoneIcon, "Mobile preview"],
          ] as const).map(([value, Icon, label]) => (
            <Button
              key={value}
              aria-label={label}
              aria-pressed={viewport === value}
              className={cn(
                "size-7 rounded-[5px] text-[#777] hover:bg-white hover:text-[#222]",
                viewport === value && "bg-white text-[#222] shadow-[0_1px_2px_rgba(0,0,0,0.05)]",
              )}
              size="icon-sm"
              title={label}
              type="button"
              variant="ghost"
              onClick={() => setViewport(value)}
            >
              <Icon className="size-3.5" />
            </Button>
          ))}
        </div>
        <div className="flex items-center gap-0.5">
          <Button
            aria-label="Copy HTML source"
            className="size-7 rounded-md text-[#777] hover:bg-[#f6f6f4] hover:text-[#222]"
            size="icon-sm"
            title="Copy source"
            type="button"
            variant="ghost"
            onClick={() => {
              void navigator.clipboard.writeText(content).then(
                () => toast.success("Artifact copied"),
                () => toast.error("Unable to copy artifact"),
              )
            }}
          >
            <CopyIcon className="size-3.5" />
          </Button>
          <Button
            aria-label="Refresh HTML preview"
            className="size-7 rounded-md text-[#777] hover:bg-[#f6f6f4] hover:text-[#222]"
            size="icon-sm"
            title="Refresh preview"
            type="button"
            variant="ghost"
            onClick={() => setRefreshRevision((revision) => revision + 1)}
          >
            <RefreshCwIcon className="size-3.5" />
          </Button>
        </div>
      </div>
      <div className="flex min-h-0 justify-center overflow-hidden p-2.5">
        <div
          className={cn(
            "h-full max-w-full overflow-hidden bg-white transition-[width] duration-200",
            viewport === "desktop" && "w-full",
            viewport === "tablet" && "w-[768px] border border-[#deded9] shadow-[0_8px_24px_rgba(0,0,0,0.06)]",
            viewport === "mobile" && "w-[390px] border border-[#deded9] shadow-[0_8px_24px_rgba(0,0,0,0.06)]",
          )}
        >
          <iframe
            key={refreshRevision}
            ref={iframeRef}
            className="size-full bg-white"
            title="HTML artifact preview"
            sandbox="allow-forms allow-scripts"
            srcDoc={previewContent}
          />
        </div>
      </div>
    </div>
  )
}

function isArtifactScrollMessage(
  data: unknown,
  key: string,
): data is {
  type: "save" | "restore-request"
  x?: unknown
  y?: unknown
} {
  return (
    typeof data === "object" &&
    data !== null &&
    "source" in data &&
    data.source === HTML_PREVIEW_SCROLL_MESSAGE_SOURCE &&
    "key" in data &&
    data.key === key &&
    "type" in data &&
    (data.type === "save" || data.type === "restore-request")
  )
}

function scrollCoordinate(value: unknown) {
  return typeof value === "number" && Number.isFinite(value) ? value : undefined
}

function useThrottledValue(value: string, intervalMs: number, resetKey: string) {
  const [throttledValue, setThrottledValue] = useState(value)
  const latestValueRef = useRef(value)
  const lastFlushAtRef = useRef(0)
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const resetKeyRef = useRef(resetKey)

  useEffect(() => {
    latestValueRef.current = value

    if (resetKeyRef.current !== resetKey) {
      resetKeyRef.current = resetKey
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current)
        timeoutRef.current = null
      }
      lastFlushAtRef.current = Date.now()
      setThrottledValue(value)
      return
    }

    if (intervalMs <= 0) {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current)
        timeoutRef.current = null
      }
      lastFlushAtRef.current = Date.now()
      setThrottledValue(value)
      return
    }

    const now = Date.now()
    const elapsed = now - lastFlushAtRef.current
    if (lastFlushAtRef.current === 0 || elapsed >= intervalMs) {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current)
        timeoutRef.current = null
      }
      lastFlushAtRef.current = now
      setThrottledValue(value)
      return
    }

    if (timeoutRef.current) {
      return
    }
    timeoutRef.current = setTimeout(() => {
      timeoutRef.current = null
      lastFlushAtRef.current = Date.now()
      setThrottledValue(latestValueRef.current)
    }, intervalMs - elapsed)
  }, [intervalMs, resetKey, value])

  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current)
      }
    }
  }, [])

  return intervalMs <= 0 || resetKeyRef.current !== resetKey ? value : throttledValue
}

function VideoPreview({ src, title }: { src: string; title: string }) {
  return (
    <div className="flex h-full items-center justify-center bg-[#111] p-4">
      <video
        className="max-h-full max-w-full rounded-md"
        controls
        preload="metadata"
        src={src}
        title={title}
      />
    </div>
  )
}

function PdfPreview({ src, title }: { src: string; title: string }) {
  type PdfRenderTask = { cancel: () => void; promise: Promise<unknown> }
  type PdfPage = {
    cleanup?: () => boolean
    getViewport: (options: { scale: number }) => { width: number; height: number }
    render: (options: {
      canvas: HTMLCanvasElement
      canvasContext: CanvasRenderingContext2D
      viewport: { width: number; height: number }
    }) => PdfRenderTask
  }
  type PdfDocument = {
    destroy: () => Promise<void>
    getPage: (pageNumber: number) => Promise<PdfPage>
    numPages: number
  }
  type PdfLoadingTask = {
    destroy: () => Promise<void>
    promise: Promise<PdfDocument>
  }

  const containerRef = useRef<HTMLDivElement | null>(null)
  const canvasRef = useRef<HTMLCanvasElement | null>(null)
  const documentRef = useRef<PdfDocument | null>(null)
  const [documentRevision, setDocumentRevision] = useState(0)
  const [layoutRevision, setLayoutRevision] = useState(0)
  const [pageNumber, setPageNumber] = useState(1)
  const [pageCount, setPageCount] = useState<number | null>(null)
  const [zoom, setZoom] = useState<(typeof PDF_ZOOM_STEPS)[number]>(1)
  const [status, setStatus] = useState<"loading" | "rendered" | "error">("loading")

  useEffect(() => {
    let cancelled = false
    let loadingTask: PdfLoadingTask | null = null

    async function loadDocument() {
      setStatus("loading")
      setPageCount(null)
      setPageNumber(1)
      setZoom(1)

      try {
        const pdfjs = await import("pdfjs-dist")
        pdfjs.GlobalWorkerOptions.workerSrc = new URL("pdfjs-dist/build/pdf.worker.mjs", import.meta.url).toString()

        loadingTask = pdfjs.getDocument(src) as unknown as PdfLoadingTask
        const loadedDocument = await loadingTask.promise
        if (cancelled) {
          await loadedDocument.destroy()
          return
        }

        documentRef.current = loadedDocument
        setPageCount(loadedDocument.numPages)
        setDocumentRevision((revision) => revision + 1)
      } catch {
        if (!cancelled) {
          setStatus("error")
        }
      }
    }

    void loadDocument()

    return () => {
      cancelled = true
      documentRef.current = null
      void loadingTask?.destroy()
    }
  }, [src])

  useEffect(() => {
    const container = containerRef.current
    if (!container || typeof ResizeObserver === "undefined") {
      return
    }

    let animationFrame = 0
    const observer = new ResizeObserver(() => {
      cancelAnimationFrame(animationFrame)
      animationFrame = requestAnimationFrame(() => {
        setLayoutRevision((revision) => revision + 1)
      })
    })
    observer.observe(container)

    return () => {
      cancelAnimationFrame(animationFrame)
      observer.disconnect()
    }
  }, [])

  useEffect(() => {
    const documentProxy = documentRef.current
    const canvas = canvasRef.current
    const container = containerRef.current
    if (!documentProxy || !canvas || !container) {
      return
    }
    const activeDocument = documentProxy
    const activeCanvas = canvas
    const activeContainer = container

    let cancelled = false
    let renderTask: PdfRenderTask | null = null
    let page: PdfPage | null = null

    async function renderPage() {
      setStatus("loading")
      try {
        page = await activeDocument.getPage(pageNumber)
        if (cancelled) {
          return
        }

        const availableWidth = Math.max(activeContainer.clientWidth - 40, 240)
        const baseViewport = page.getViewport({ scale: 1 })
        const fitScale = Math.max(0.4, Math.min(2, availableWidth / baseViewport.width))
        const viewport = page.getViewport({ scale: fitScale * zoom })
        const pixelRatio = Math.min(window.devicePixelRatio || 1, 2)
        const context = activeCanvas.getContext("2d")
        if (!context) {
          throw new Error("Canvas is unavailable")
        }

        activeCanvas.width = Math.floor(viewport.width * pixelRatio)
        activeCanvas.height = Math.floor(viewport.height * pixelRatio)
        activeCanvas.style.width = `${Math.floor(viewport.width)}px`
        activeCanvas.style.height = `${Math.floor(viewport.height)}px`
        context.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0)
        context.clearRect(0, 0, viewport.width, viewport.height)

        renderTask = page.render({ canvas: activeCanvas, canvasContext: context, viewport })
        await renderTask.promise
        if (!cancelled) {
          setStatus("rendered")
        }
      } catch {
        if (!cancelled) {
          setStatus("error")
        }
      }
    }

    void renderPage()

    return () => {
      cancelled = true
      renderTask?.cancel()
      page?.cleanup?.()
    }
  }, [documentRevision, layoutRevision, pageNumber, zoom])

  const zoomIndex = PDF_ZOOM_STEPS.indexOf(zoom)
  const zoomOut = () => setZoom(PDF_ZOOM_STEPS[Math.max(zoomIndex - 1, 0)] ?? 1)
  const zoomIn = () => setZoom(PDF_ZOOM_STEPS[Math.min(zoomIndex + 1, PDF_ZOOM_STEPS.length - 1)] ?? 1)

  return (
    <div className="absolute inset-0 min-h-0 bg-[#f7f7f7]">
      <div ref={containerRef} className="size-full overflow-auto px-5 pb-16 pt-16">
        <canvas
          ref={canvasRef}
          aria-label={`PDF page ${pageNumber}${pageCount ? ` of ${pageCount}` : ""}`}
          className="mx-auto block h-fit shrink-0 rounded-md border border-[#e2e2de] bg-white shadow-[0_8px_30px_rgba(0,0,0,0.07)]"
        />
      </div>
      {status === "loading" && (
        <div className="absolute inset-0 z-10 flex items-center justify-center bg-[#f7f7f7]/70">
          <Spinner className="text-muted-foreground" />
        </div>
      )}
      {status === "error" && (
        <div className="absolute inset-0 flex items-center justify-center bg-[#f7f7f7] p-6 text-center text-xs text-[#6f6f69]">
          PDF page preview is unavailable. Use Open or Download to inspect the document.
        </div>
      )}
      <div className="pointer-events-none absolute left-3 top-3 z-20 max-w-[calc(100%-1.5rem)] rounded-md border border-[#e4e4df] bg-white/90 px-3 py-2 text-xs shadow-[0_1px_2px_rgba(0,0,0,0.05)] backdrop-blur">
        <div className="truncate font-medium text-[#2c2c2a]">{title}</div>
        <div className="mt-0.5 text-[#8a8a86]">
          {pageCount ? `PDF document · ${pageCount} page${pageCount === 1 ? "" : "s"}` : "PDF document"}
        </div>
      </div>
      {status !== "error" && pageCount && (
        <div className="absolute bottom-3 left-1/2 z-20 flex max-w-[calc(100%-1.5rem)] -translate-x-1/2 items-center gap-1 rounded-md border border-[#deded9] bg-white/95 p-1 shadow-[0_4px_16px_rgba(0,0,0,0.08)] backdrop-blur">
          <Button
            aria-label="Previous PDF page"
            disabled={pageNumber <= 1}
            size="icon-sm"
            title="Previous page"
            type="button"
            variant="ghost"
            onClick={() => setPageNumber((current) => Math.max(current - 1, 1))}
          >
            <ChevronLeftIcon className="size-3.5" />
          </Button>
          <span className="min-w-14 px-1 text-center text-[11px] font-medium tabular-nums text-[#565653]">
            {pageNumber} / {pageCount}
          </span>
          <Button
            aria-label="Next PDF page"
            disabled={pageNumber >= pageCount}
            size="icon-sm"
            title="Next page"
            type="button"
            variant="ghost"
            onClick={() => setPageNumber((current) => Math.min(current + 1, pageCount))}
          >
            <ChevronRightIcon className="size-3.5" />
          </Button>
          <span aria-hidden="true" className="mx-0.5 h-4 w-px bg-[#e7e7e3]" />
          <Button
            aria-label="Zoom PDF out"
            disabled={zoomIndex <= 0}
            size="icon-sm"
            title="Zoom out"
            type="button"
            variant="ghost"
            onClick={zoomOut}
          >
            <MinusIcon className="size-3.5" />
          </Button>
          <span className="min-w-10 px-1 text-center text-[11px] font-medium tabular-nums text-[#565653]">
            {Math.round(zoom * 100)}%
          </span>
          <Button
            aria-label="Zoom PDF in"
            disabled={zoomIndex >= PDF_ZOOM_STEPS.length - 1}
            size="icon-sm"
            title="Zoom in"
            type="button"
            variant="ghost"
            onClick={zoomIn}
          >
            <PlusIcon className="size-3.5" />
          </Button>
          <Button
            aria-label="Fit PDF to width"
            disabled={zoom === 1}
            size="icon-sm"
            title="Fit to width"
            type="button"
            variant="ghost"
            onClick={() => setZoom(1)}
          >
            <RotateCcwIcon className="size-3.5" />
          </Button>
        </div>
      )}
    </div>
  )
}

function AudioPreview({ src, title }: { src: string; title: string }) {
  return (
    <div className="flex h-full items-center justify-center bg-[#f7f7f7] p-6">
      <div className="w-full max-w-md rounded-lg border border-[#e4e4df] bg-white p-4 shadow-[0_1px_2px_rgba(0,0,0,0.03)]">
        <div className="mb-3 min-w-0">
          <div className="truncate text-sm font-medium text-[#242424]">{title}</div>
          <div className="mt-1 text-xs text-[#8a8a86]">Audio artifact preview</div>
        </div>
        <audio className="w-full" controls preload="metadata" src={src} />
      </div>
    </div>
  )
}

function UnsupportedArtifactPreview({ filename, typeLabel }: { filename: string; typeLabel: string }) {
  return (
    <div className="flex h-full items-center justify-center bg-[#f7f7f7] p-6">
      <div className="max-w-sm rounded-lg border border-[#e4e4df] bg-white p-5 text-center shadow-[0_1px_2px_rgba(0,0,0,0.03)]">
        <div className="text-sm font-medium text-[#242424]">{filename}</div>
        <div className="mt-1 text-xs text-[#8a8a86]">{typeLabel}</div>
        <p className="mt-4 text-xs leading-5 text-[#6f6f69]">
          Preview is not available for this artifact type. Download it to inspect the full file.
        </p>
      </div>
    </div>
  )
}

function ArtifactCodeView({ content, ext }: { content: string; ext: string }) {
  const language = languageForExtension(ext)

  if (!language || content.length > HIGHLIGHT_MAX_CHARS) {
    return (
      <pre className="h-full overflow-auto bg-[#fbfbfb] p-4 text-xs leading-5 text-[#242424]">
        <code>{content}</code>
      </pre>
    )
  }

  return (
    <div className="h-full overflow-auto bg-[#fbfbfb] text-[#242424] [&_pre]:!bg-transparent [&_pre]:p-4 [&_pre]:text-xs [&_code]:text-xs">
      <CodeBlockContent code={content} language={language} showLineNumbers />
    </div>
  )
}

function CsvPreview({ content }: { content: string }) {
  const preview = useMemo(() => parseCsvPreview(content), [content])

  if (preview.rows.length === 0) {
    return (
      <div className="flex h-full items-center justify-center p-6 text-sm text-muted-foreground">
        Empty CSV artifact
      </div>
    )
  }

  const [header, ...bodyRows] = preview.rows

  return (
    <div className="flex h-full min-h-0 flex-col bg-white">
      <div className="flex shrink-0 items-center justify-between gap-3 border-b border-[#eeeeec] bg-[#fbfbfa] px-3 py-2 pr-12">
        <div className="min-w-0 text-xs font-medium text-[#383836]">CSV preview</div>
        <div className="shrink-0 text-[11px] text-[#8a8a86]">
          {preview.totalRows} rows · {preview.totalColumns} columns
        </div>
      </div>
      <div className="min-h-0 flex-1 overflow-auto">
        <table className="min-w-full border-separate border-spacing-0 text-left text-xs">
          <thead>
            <tr>
              {header.map((cell, index) => (
                <th
                  key={`${index}-${cell}`}
                  className="sticky top-0 z-10 max-w-[180px] border-b border-r border-[#eeeeec] bg-[#f7f7f5] px-3 py-2 font-medium text-[#383836]"
                  title={cell}
                >
                  <span className="block truncate">{cell || `Column ${index + 1}`}</span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {bodyRows.map((row, rowIndex) => (
              <tr key={rowIndex} className="odd:bg-white even:bg-[#fcfcfb]">
                {row.map((cell, cellIndex) => (
                  <td
                    key={`${rowIndex}-${cellIndex}`}
                    className="max-w-[180px] border-b border-r border-[#f1f1ef] px-3 py-2 text-[#4b4b48]"
                    title={cell}
                  >
                    <span className="block truncate">{cell}</span>
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
        {(preview.truncatedRows || preview.truncatedColumns) && (
          <div className="border-t border-[#eeeeec] bg-[#fbfbfa] px-3 py-2 text-[11px] text-[#8a8a86]">
            Preview limited to {CSV_MAX_ROWS} rows and {CSV_MAX_COLUMNS} columns.
          </div>
        )}
      </div>
    </div>
  )
}

function extension(path: string) {
  const name = fileName(path)
  const ext = name.split(".").pop()
  return ext && ext !== name ? ext.toLowerCase() : fileExtension(path).toLowerCase()
}

function languageForExtension(ext: string): BundledLanguage | null {
  switch (ext) {
    case "css":
      return "css"
    case "csv":
      return "csv"
    case "html":
      return "html"
    case "js":
      return "javascript"
    case "json":
      return "json"
    case "jsx":
      return "jsx"
    case "md":
      return "markdown"
    case "py":
      return "python"
    case "sh":
      return "shellscript"
    case "sql":
      return "sql"
    case "svg":
    case "xml":
      return "xml"
    case "ts":
      return "typescript"
    case "tsx":
      return "tsx"
    case "yaml":
    case "yml":
      return "yaml"
    default:
      return null
  }
}

function parseCsvPreview(content: string) {
  const rawRows = parseCsvRows(content)
  const rows = rawRows.filter((row, index) => index < rawRows.length - 1 || row.some((cell) => cell.length > 0))
  const totalColumns = rows.reduce((max, row) => Math.max(max, row.length), 0)
  const visibleColumns = Math.min(totalColumns, CSV_MAX_COLUMNS)
  const visibleRows = rows.slice(0, CSV_MAX_ROWS).map((row) => {
    const cells = Array.from({ length: visibleColumns }, (_, index) => row[index] ?? "")
    return cells
  })

  return {
    rows: visibleRows,
    totalRows: rows.length,
    totalColumns,
    truncatedRows: rows.length > CSV_MAX_ROWS,
    truncatedColumns: totalColumns > CSV_MAX_COLUMNS,
  }
}

function parseCsvRows(content: string) {
  const rows: string[][] = []
  let row: string[] = []
  let cell = ""
  let inQuotes = false

  for (let index = 0; index < content.length; index += 1) {
    const char = content[index]
    const next = content[index + 1]

    if (inQuotes) {
      if (char === "\"" && next === "\"") {
        cell += "\""
        index += 1
      } else if (char === "\"") {
        inQuotes = false
      } else {
        cell += char
      }
      continue
    }

    if (char === "\"") {
      inQuotes = true
    } else if (char === ",") {
      row.push(cell)
      cell = ""
    } else if (char === "\n" || char === "\r") {
      row.push(cell)
      rows.push(row)
      row = []
      cell = ""
      if (char === "\r" && next === "\n") {
        index += 1
      }
    } else {
      cell += char
    }
  }

  if (content.length > 0 || cell || row.length > 0) {
    row.push(cell)
    rows.push(row)
  }

  return rows
}
