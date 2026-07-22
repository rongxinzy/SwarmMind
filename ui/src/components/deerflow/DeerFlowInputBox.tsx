"use client"

import {
  CheckIcon,
  GraduationCapIcon,
  LightbulbIcon,
  PaperclipIcon,
  RocketIcon,
  XIcon,
  ZapIcon,
} from "lucide-react"
import { useCallback, useEffect, useMemo, useState } from "react"
import { toast } from "sonner"

import {
  ModelSelector,
  ModelSelectorContent,
  ModelSelectorInput,
  ModelSelectorItem,
  ModelSelectorList,
  ModelSelectorName,
  ModelSelectorTrigger,
} from "@/components/ai-elements/model-selector"
import { Suggestion, Suggestions } from "@/components/ai-elements/suggestion"
import {
  PromptInput,
  PromptInputActionMenu,
  PromptInputActionMenuContent,
  PromptInputActionMenuItem,
  PromptInputActionMenuTrigger,
  PromptInputBody,
  PromptInputButton,
  PromptInputFooter,
  PromptInputSubmit,
  PromptInputTextarea,
  PromptInputTools,
  usePromptInputAttachments,
} from "@/components/ai-elements/prompt-input"
import {
  DropdownMenuGroup,
  DropdownMenuLabel,
} from "@/components/ui/dropdown-menu"
import type { DeerFlowPromptInputMessage } from "@/core/deerflow/input"
import { apiFetchJson } from "@/lib/api"
import { cn } from "@/lib/utils"
import type { ChatStatus } from "@/types/chat"

export type DeerFlowInputMode = "flash" | "thinking" | "pro" | "ultra"

interface RuntimeModelOption {
  name: string
  provider: string
  model: string
  display_name?: string | null
  description?: string | null
  supports_vision: boolean
  supports_thinking: boolean
  capability_tags: string[]
  is_default: boolean
}

interface RuntimeModelCatalogResponse {
  models: RuntimeModelOption[]
  default_model?: string | null
}

interface DeerFlowInputBoxProps {
  className?: string
  value: string
  onValueChange: (value: string) => void
  status: ChatStatus
  mode: DeerFlowInputMode
  modelName?: string
  placement?: "empty" | "docked"
  autoFocus?: boolean
  disabled?: boolean
  followups?: string[]
  followupsLoading?: boolean
  onModeChange: (mode: DeerFlowInputMode) => void
  onModelChange: (modelName: string | undefined) => void
  onFollowupSelect?: (suggestion: string) => void
  onFollowupsDismiss?: () => void
  onSubmit: (message: DeerFlowPromptInputMessage) => void | Promise<void>
  onStop?: () => void
}

const MODE_COPY: Record<
  DeerFlowInputMode,
  {
    label: string
    description: string
    icon: typeof ZapIcon
    effort: string
  }
> = {
  flash: {
    label: "Flash",
    description: "快速响应，适合轻量问答和直接执行。",
    icon: ZapIcon,
    effort: "快速",
  },
  thinking: {
    label: "Thinking",
    description: "启用推理过程，适合需要分析的问题。",
    icon: LightbulbIcon,
    effort: "思考",
  },
  pro: {
    label: "Pro",
    description: "推理 + 规划，适合复杂交付主路径。",
    icon: GraduationCapIcon,
    effort: "规划",
  },
  ultra: {
    label: "Ultra",
    description: "推理 + 规划 + 子任务协作，适合长任务。",
    icon: RocketIcon,
    effort: "协作",
  },
}

const MODE_ORDER: DeerFlowInputMode[] = ["flash", "thinking", "pro", "ultra"]

function getModelCapabilityLabel(model: RuntimeModelOption | undefined) {
  if (!model) {
    return "model"
  }
  if (model.supports_thinking) {
    return "thinking"
  }
  if (model.supports_vision) {
    return "vision"
  }
  return model.provider
}

export function DeerFlowInputBox({
  className,
  value,
  onValueChange,
  status,
  mode,
  modelName,
  placement = "docked",
  autoFocus,
  disabled,
  followups = [],
  followupsLoading = false,
  onModeChange,
  onModelChange,
  onFollowupSelect,
  onFollowupsDismiss,
  onSubmit,
  onStop,
}: DeerFlowInputBoxProps) {
  const [modelDialogOpen, setModelDialogOpen] = useState(false)
  const [models, setModels] = useState<RuntimeModelOption[]>([])
  const [modelsLoading, setModelsLoading] = useState(false)

  useEffect(() => {
    let cancelled = false
    setModelsLoading(true)
    apiFetchJson<RuntimeModelCatalogResponse>("/runtime/models")
      .then((catalog) => {
        if (cancelled) {
          return
        }
        setModels(catalog.models)
      })
      .catch(() => {
        if (!cancelled) {
          setModels([])
        }
      })
      .finally(() => {
        if (!cancelled) {
          setModelsLoading(false)
        }
      })

    return () => {
      cancelled = true
    }
  }, [])

  const selectedModel = useMemo(() => {
    if (models.length === 0) {
      return undefined
    }
    return (
      models.find((model) => model.name === modelName) ??
      models.find((model) => model.is_default) ??
      models[0]
    )
  }, [modelName, models])

  const supportsThinking = selectedModel?.supports_thinking ?? false

  useEffect(() => {
    if (!selectedModel) {
      return
    }
    if (modelName !== selectedModel.name) {
      onModelChange(selectedModel.name)
    }
    if (!supportsThinking && mode !== "flash") {
      onModeChange("flash")
    }
    if (supportsThinking && !mode) {
      onModeChange("pro")
    }
  }, [mode, modelName, onModeChange, onModelChange, selectedModel, supportsThinking])

  const activeMode = !supportsThinking && mode !== "flash" ? "flash" : mode
  const modeConfig = MODE_COPY[activeMode]
  const ModeIcon = modeConfig.icon
  const isGenerating = status === "submitted" || status === "streaming"
  const showFollowups = !disabled && (followupsLoading || followups.length > 0)

  const handleModelSelect = useCallback(
    (nextModelName: string) => {
      const model = models.find((item) => item.name === nextModelName)
      if (!model) {
        return
      }
      onModelChange(model.name)
      if (!model.supports_thinking && mode !== "flash") {
        onModeChange("flash")
      }
      setModelDialogOpen(false)
    },
    [mode, models, onModeChange, onModelChange],
  )

  const handleModeSelect = useCallback(
    (nextMode: DeerFlowInputMode) => {
      if (nextMode !== "flash" && !supportsThinking) {
        onModeChange("flash")
        return
      }
      onModeChange(nextMode)
    },
    [onModeChange, supportsThinking],
  )

  return (
    <div className="flex w-full flex-col gap-2">
      {showFollowups && (
        <div className="flex justify-center">
          {followupsLoading ? (
            <div className="rounded-full border border-[#e8e8e8] bg-white/85 px-4 py-2 text-xs text-[#6f6f6f] shadow-sm backdrop-blur-sm">
              正在生成后续建议...
            </div>
          ) : (
            <div className="flex max-w-full items-start gap-2">
              <Suggestions className="justify-center">
                {followups.map((suggestion) => (
                  <Suggestion
                    key={suggestion}
                    suggestion={suggestion}
                    className="border-[#e8e8e8] bg-white/90 text-[#3f3f3f] shadow-[0_1px_2px_rgba(0,0,0,0.03)] hover:bg-[#fafafa]"
                    onClick={onFollowupSelect}
                  />
                ))}
              </Suggestions>
              {onFollowupsDismiss && (
                <button
                  type="button"
                  className="mt-1 inline-flex size-7 shrink-0 items-center justify-center rounded-full border border-[#e8e8e8] bg-white/90 text-[#8a8a8a] shadow-sm hover:text-[#242424]"
                  aria-label="关闭后续建议"
                  onClick={onFollowupsDismiss}
                >
                  <XIcon className="size-3.5" />
                </button>
              )}
            </div>
          )}
        </div>
      )}
      <PromptInput
        onSubmit={onSubmit}
        globalDrop
        multiple
        maxFiles={8}
        maxFileSize={50 * 1024 * 1024}
        onError={(error) => toast.error(error.message)}
        className={cn(
          "focus-glow flex w-full flex-col border border-[#dfdfdf] bg-white/95 p-3 backdrop-blur-sm transition-all",
          placement === "empty"
            ? "rounded-[1.625rem] shadow-[0_22px_70px_rgba(0,0,0,0.09)]"
            : "rounded-[1.5rem] shadow-[0_12px_42px_rgba(0,0,0,0.07)]",
          className,
        )}
        style={{ minHeight: placement === "empty" ? "8.5rem" : "8.25rem", maxHeight: "20rem" }}
      >
        <PromptInputBody>
          <PromptInputTextarea
            value={value}
            onChange={(event) => onValueChange(event.currentTarget.value)}
            placeholder="Ask SwarmMind to create, research, analyze, or ship something..."
            className="min-h-[6.75rem] text-[15px] leading-6 text-[#171717] placeholder:text-[#8a8a8a]"
            disabled={disabled === true || isGenerating}
            autoFocus={autoFocus}
          />
          <AttachmentPreview disabled={disabled === true || isGenerating} />
        </PromptInputBody>
        <PromptInputFooter className="flex-wrap items-center justify-between gap-x-2 gap-y-0 border-t border-[#f0f0f0] py-1 sm:flex-nowrap">
          <PromptInputTools className="flex-1">
            <AttachmentButton disabled={disabled === true || isGenerating} />
            <PromptInputActionMenu>
              <PromptInputActionMenuTrigger className="h-7 gap-1.5 rounded-lg px-2 text-[#242424] hover:bg-[#f6f6f6]">
                <ModeIcon className={cn("size-3.5", activeMode === "ultra" && "text-[#dabb5e]")} />
                <span className={cn("text-xs font-normal", activeMode === "ultra" && "text-[#8a6d18]")}>
                  {modeConfig.label}
                </span>
              </PromptInputActionMenuTrigger>
              <PromptInputActionMenuContent className="w-80">
                <DropdownMenuGroup>
                  <DropdownMenuLabel className="text-xs text-muted-foreground">
                    Run mode
                  </DropdownMenuLabel>
                  {MODE_ORDER.map((option) => {
                    const config = MODE_COPY[option]
                    const Icon = config.icon
                    const unavailable = option !== "flash" && !supportsThinking
                    return (
                      <PromptInputActionMenuItem
                        key={option}
                        className={cn(
                          "items-start gap-3 py-2",
                          activeMode === option ? "text-accent-foreground" : "text-muted-foreground/75",
                        )}
                        disabled={unavailable}
                        onSelect={() => handleModeSelect(option)}
                      >
                        <Icon className={cn("mt-0.5 size-4", option === "ultra" && activeMode === "ultra" && "text-[#dabb5e]")} />
                        <div className="flex min-w-0 flex-1 flex-col gap-1">
                          <div className="flex items-center gap-2 font-medium">
                            {config.label}
                            <span className="rounded-full bg-muted px-1.5 py-0.5 text-[10px] font-normal text-muted-foreground">
                              {config.effort}
                            </span>
                          </div>
                          <div className="text-xs leading-4">
                            {unavailable ? "当前模型未声明 supports_thinking，已降级为 Flash。" : config.description}
                          </div>
                        </div>
                        {activeMode === option ? <CheckIcon className="ml-auto size-4" /> : <div className="ml-auto size-4" />}
                      </PromptInputActionMenuItem>
                    )
                  })}
                </DropdownMenuGroup>
              </PromptInputActionMenuContent>
            </PromptInputActionMenu>
          </PromptInputTools>
          <PromptInputTools className="ml-auto max-w-full shrink-0 justify-end">
            <ModelSelector open={modelDialogOpen} onOpenChange={setModelDialogOpen}>
              <ModelSelectorTrigger
                render={
                  <PromptInputButton
                    size="sm"
                    className="h-7 min-w-[4rem] max-w-[8rem] shrink rounded-lg px-2 hover:bg-[#f6f6f6] sm:max-w-[14rem]"
                  />
                }
              >
                <div className="flex min-w-0 items-center gap-1.5 overflow-hidden text-left">
                  <ModelSelectorName className="hidden max-w-[9.5rem] truncate text-xs font-normal sm:block">
                    {modelsLoading ? "加载模型..." : selectedModel?.display_name ?? selectedModel?.name ?? "默认模型"}
                  </ModelSelectorName>
                  {selectedModel && (
                    <span className="shrink-0 rounded-full border border-[#ececec] px-1.5 py-0.5 text-[10px] font-normal text-[#6f6f6f]">
                      {getModelCapabilityLabel(selectedModel)}
                    </span>
                  )}
                </div>
              </ModelSelectorTrigger>
              <ModelSelectorContent title="Select model">
                <ModelSelectorInput placeholder="搜索模型" />
                <ModelSelectorList>
                  {models.map((model) => (
                    <ModelSelectorItem
                      key={model.name}
                      value={model.name}
                      onSelect={() => handleModelSelect(model.name)}
                    >
                      <div className="flex min-w-0 flex-1 flex-col">
                        <ModelSelectorName>{model.display_name ?? model.name}</ModelSelectorName>
                        <span className="truncate text-[10px] text-muted-foreground">
                          {model.provider} · {model.model}
                        </span>
                        <span className="truncate text-[10px] text-muted-foreground/80">
                          {model.capability_tags.join(" / ")}
                        </span>
                      </div>
                      {model.name === selectedModel?.name ? <CheckIcon className="ml-auto size-4" /> : <div className="ml-auto size-4" />}
                    </ModelSelectorItem>
                  ))}
                </ModelSelectorList>
              </ModelSelectorContent>
            </ModelSelector>
            <PromptInputSubmit
              status={status}
              onStop={onStop}
              disabled={disabled === true || (!isGenerating && !value.trim())}
              className="size-7 rounded-full border border-[#68686878] bg-[#111111] text-white shadow-[0_2px_8px_rgba(0,0,0,0.14)] hover:bg-[#232323] disabled:border-transparent disabled:bg-[#d9d9d9] disabled:text-white disabled:shadow-none"
            />
          </PromptInputTools>
        </PromptInputFooter>
      </PromptInput>
    </div>
  )
}

function AttachmentButton({ disabled }: { disabled?: boolean }) {
  const attachments = usePromptInputAttachments()

  return (
    <PromptInputButton
      type="button"
      className="h-7 rounded-lg px-2 text-[#5f5f5f] hover:bg-[#f6f6f6]"
      tooltip="添加文件"
      disabled={disabled}
      onClick={() => attachments.openFileDialog()}
    >
      <PaperclipIcon className="size-3.5" />
    </PromptInputButton>
  )
}

function AttachmentPreview({ disabled }: { disabled?: boolean }) {
  const attachments = usePromptInputAttachments()

  if (attachments.files.length === 0) {
    return null
  }

  return (
    <div className="mt-2 flex max-h-20 flex-wrap gap-1.5 overflow-y-auto pr-1">
      {attachments.files.map((file) => (
        <span
          key={file.id}
          className="group inline-flex max-w-[14rem] items-center gap-1.5 rounded-lg border border-[#e8e8e8] bg-[#fbfbfb] px-2 py-1 text-[11px] text-[#3f3f3f]"
        >
          <PaperclipIcon className="size-3 shrink-0 text-[#8a8a8a]" />
          <span className="truncate">{file.filename ?? "file"}</span>
          <button
            type="button"
            className="rounded p-0.5 text-[#9a9a9a] transition-colors hover:bg-[#eeeeee] hover:text-[#242424]"
            disabled={disabled}
            onClick={() => attachments.remove(file.id)}
            aria-label={`移除 ${file.filename ?? "file"}`}
          >
            <XIcon className="size-3" />
          </button>
        </span>
      ))}
    </div>
  )
}
