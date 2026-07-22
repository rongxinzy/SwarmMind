"use client"

import { CheckIcon } from "lucide-react"
import { useCallback, useEffect, useMemo, useState } from "react"

import {
  ModelSelector,
  ModelSelectorContent,
  ModelSelectorInput,
  ModelSelectorItem,
  ModelSelectorList,
  ModelSelectorName,
  ModelSelectorTrigger,
} from "@/components/ai-elements/model-selector"
import {
  PromptInput,
  PromptInputBody,
  PromptInputButton,
  PromptInputFooter,
  PromptInputSubmit,
  PromptInputTextarea,
  PromptInputTools,
} from "@/components/ai-elements/prompt-input"
import { cn } from "@/lib/utils"

export interface ChatModelInfo {
  id: string
  name: string
  provider: string
  model: string
  display_name: string
  description?: string | null
  supports_vision: boolean
  supports_thinking: boolean
  is_default: boolean
}

export type DirectChatStatus = "ready" | "streaming" | "error"

interface ChatInputBoxProps {
  value: string
  onValueChange: (value: string) => void
  status: DirectChatStatus
  models: ChatModelInfo[]
  selectedModelId: string | null
  isLoadingModels: boolean
  placement?: "empty" | "docked"
  autoFocus?: boolean
  onModelChange: (modelId: string) => void
  onSubmit: () => void | Promise<void>
  onStop?: () => void
}

function getModelCapabilityLabel(model: ChatModelInfo | undefined) {
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

export function ChatInputBox({
  value,
  onValueChange,
  status,
  models,
  selectedModelId,
  isLoadingModels,
  placement = "docked",
  autoFocus,
  onModelChange,
  onSubmit,
  onStop,
}: ChatInputBoxProps) {
  const [modelDialogOpen, setModelDialogOpen] = useState(false)

  const selectedModel = useMemo(() => {
    if (models.length === 0) {
      return undefined
    }
    return (
      models.find((model) => model.id === selectedModelId) ??
      models.find((model) => model.is_default) ??
      models[0]
    )
  }, [models, selectedModelId])

  useEffect(() => {
    if (selectedModel && selectedModelId !== selectedModel.id) {
      onModelChange(selectedModel.id)
    }
  }, [selectedModel, selectedModelId, onModelChange])

  const isStreaming = status === "streaming"

  const handleModelSelect = useCallback(
    (nextModelId: string) => {
      const model = models.find((item) => item.id === nextModelId)
      if (!model) {
        return
      }
      onModelChange(model.id)
      setModelDialogOpen(false)
    },
    [models, onModelChange],
  )

  const handleSubmit = useCallback(async () => {
    if (!value.trim() || isStreaming) {
      return
    }
    await onSubmit()
  }, [value, isStreaming, onSubmit])

  return (
    <PromptInput
      onSubmit={handleSubmit}
      className={cn(
        "focus-glow flex w-full flex-col border border-[#dfdfdf] bg-white/95 p-3 backdrop-blur-sm transition-all",
        placement === "empty"
          ? "rounded-[1.625rem] shadow-[0_22px_70px_rgba(0,0,0,0.09)]"
          : "rounded-[1.5rem] shadow-[0_12px_42px_rgba(0,0,0,0.07)]",
      )}
      style={{ minHeight: placement === "empty" ? "8.5rem" : "8.25rem", maxHeight: "20rem" }}
    >
      <PromptInputBody>
        <PromptInputTextarea
          value={value}
          onChange={(event) => onValueChange(event.currentTarget.value)}
          placeholder="有什么可以帮你的？"
          className="min-h-[6.75rem] text-[15px] leading-6 text-[#171717] placeholder:text-[#8a8a8a]"
          disabled={isStreaming}
          autoFocus={autoFocus}
        />
      </PromptInputBody>
      <PromptInputFooter className="flex-wrap items-center justify-between gap-x-2 gap-y-0 border-t border-[#f0f0f0] pt-1 pb-1 sm:flex-nowrap">
        <PromptInputTools className="flex-1" />
        <PromptInputTools className="ml-auto max-w-full shrink-0 justify-end">
          <ModelSelector open={modelDialogOpen} onOpenChange={setModelDialogOpen}>
            <ModelSelectorTrigger
              render={
                <PromptInputButton
                  size="sm"
                  className="flex h-7 min-w-[4rem] max-w-[8rem] items-center justify-center gap-1.5 rounded-lg px-2 hover:bg-[#f6f6f6] sm:max-w-[14rem]"
                />
              }
            >
              <div className="flex min-w-0 items-center gap-1.5 overflow-hidden text-left">
                <ModelSelectorName className="hidden max-w-[9.5rem] truncate text-xs font-normal sm:block">
                  {isLoadingModels
                    ? "加载模型..."
                    : selectedModel?.display_name ?? selectedModel?.name ?? "默认模型"}
                </ModelSelectorName>
                {selectedModel && (
                  <span className="shrink-0 rounded-full border border-[#ececec] px-1.5 py-0.5 text-[10px] font-normal text-[#6f6f6f]">
                    {getModelCapabilityLabel(selectedModel)}
                  </span>
                )}
              </div>
            </ModelSelectorTrigger>
            <ModelSelectorContent title="选择模型">
              <ModelSelectorInput placeholder="搜索模型" />
              <ModelSelectorList>
                {models.map((model) => (
                  <ModelSelectorItem
                    key={model.id}
                    value={model.id}
                    onSelect={() => handleModelSelect(model.id)}
                  >
                    <div className="flex min-w-0 flex-1 flex-col">
                      <ModelSelectorName>{model.display_name ?? model.name}</ModelSelectorName>
                      <span className="truncate text-[10px] text-muted-foreground">
                        {model.provider} · {model.model}
                      </span>
                      {model.description && (
                        <span className="truncate text-[10px] text-muted-foreground/80">
                          {model.description}
                        </span>
                      )}
                    </div>
                    {model.id === selectedModel?.id ? (
                      <CheckIcon className="ml-auto size-4" />
                    ) : (
                      <div className="ml-auto size-4" />
                    )}
                  </ModelSelectorItem>
                ))}
              </ModelSelectorList>
            </ModelSelectorContent>
          </ModelSelector>
          <PromptInputSubmit
            status={status === "streaming" ? "streaming" : "ready"}
            onStop={onStop}
            disabled={isStreaming ? false : !value.trim()}
            className="size-7 rounded-full border border-[#68686878] bg-[#111111] text-white shadow-[0_2px_8px_rgba(0,0,0,0.14)] hover:bg-[#232323] disabled:border-transparent disabled:bg-[#d9d9d9] disabled:text-white disabled:shadow-none"
          />
        </PromptInputTools>
      </PromptInputFooter>
    </PromptInput>
  )
}
