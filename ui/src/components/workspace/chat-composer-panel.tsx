import type { ChangeEvent, KeyboardEvent, RefObject } from "react";
import React, { useEffect, useRef } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { ArrowUp, Check, Loader2, Paperclip, Square, XIcon } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { ModePicker, ModelPicker } from "@/components/workspace/chat-controls";
import type { ConversationMode, RuntimeModelOption, RuntimeState, StreamStatus, StreamStep } from "@/core/chat/types";
import { cn } from "@/lib/utils";

interface ChatComposerPanelProps {
  attachedFiles: File[];
  error?: unknown;
  fetchModels: () => void;
  fileInputRef: RefObject<HTMLInputElement | null>;
  handleFileSelect: (event: ChangeEvent<HTMLInputElement>) => void;
  handleRemoveFile: (index: number) => void;
  handleSubmit: () => void;
  onStop?: () => void;
  input: string;
  isComposerDisabled: boolean;
  isLoading: boolean;
  isModelsLoading: boolean;
  modelLoadError: string | null;
  modelOptions: RuntimeModelOption[];
  onInputChange: (value: string) => void;
  onKeyDown: (event: KeyboardEvent<HTMLTextAreaElement>) => void;
  runtime: RuntimeState;
  selectedMode: ConversationMode;
  selectedModel: string;
  setSelectedMode: (mode: ConversationMode) => void;
  setSelectedModel: (model: string) => void;
  isEmpty?: boolean;
  quickPrompts?: {
    title: string;
    subtitle: string;
    prompt: string;
    tag: string;
    uses: string;
    gradient: string;
  }[];
  onQuickPromptSelect?: (prompt: string) => void;
  streamStatus?: StreamStatus;
  streamStep?: StreamStep | null;
  streamLabel?: string | null;
}

export function ChatComposerPanel({
  attachedFiles,
  fetchModels,
  fileInputRef,
  handleFileSelect,
  handleRemoveFile,
  handleSubmit,
  onStop,
  input,
  isComposerDisabled,
  isLoading,
  isModelsLoading,
  modelLoadError,
  modelOptions,
  onInputChange,
  onKeyDown,
  runtime,
  selectedMode,
  selectedModel,
  setSelectedMode,
  setSelectedModel,
  isEmpty = false,
  quickPrompts = [],
  onQuickPromptSelect,
}: ChatComposerPanelProps) {
  const pickerPlacement = isEmpty ? "bottom" : "top";
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    const next = Math.min(Math.max(el.scrollHeight, 88), 220);
    el.style.height = `${next}px`;
  }, [input]);

  return (
    <div
      className={cn(
        "z-20",
        isEmpty ? "relative mx-auto" : "sticky bottom-0",
      )}
      style={{
        background:
          "linear-gradient(to top, var(--codex-bg) 0%, var(--codex-bg) 85%, transparent 100%)",
      }}
    >
      <div className="relative bg-background">
        <div className="mx-auto w-full max-w-[820px] px-6 pt-0 pb-0">
          <div
            className="overflow-visible rounded-[28px] border-[1.5px] border-[rgba(210,210,207,1)] bg-card transition-all duration-200 focus-within:border-[rgba(196,196,192,1)]"
            style={{ boxShadow: "0 8px 22px rgba(24, 24, 27, 0.06)" }}
          >
            <div className="rounded-[28px] bg-card">
            <AnimatePresence>
              {runtime.activities.length > 0 && (
                <motion.div
                  key="activities"
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                  transition={{ duration: 0.2, ease: [0.16, 1, 0.3, 1] }}
                  className="overflow-hidden"
                >
                  <div className="flex flex-col gap-1 border-b border-border px-4 py-2">
                    {runtime.activities.slice(0, 5).map((activity) => (
                      <div key={activity.id} className="flex items-center gap-2 text-xs">
                        {activity.status === "running" ? (
                          <Loader2 className="size-3 shrink-0 animate-spin text-[var(--status-running)]" />
                        ) : (
                          <Check className="size-3 shrink-0 text-[var(--status-done)]" />
                        )}
                        <span
                          className={cn(
                            "truncate",
                            activity.status === "running"
                              ? "text-foreground"
                              : "text-muted-foreground",
                          )}
                        >
                          {activity.label}
                        </span>
                        {activity.detail ? (
                          <span className="ml-auto max-w-[120px] shrink-0 truncate text-muted-foreground/70">
                            {activity.detail}
                          </span>
                        ) : null}
                      </div>
                    ))}
                    {runtime.activities.length > 5 ? (
                      <p className="pl-5 text-xs text-muted-foreground/70">
                        +{runtime.activities.length - 5} 个任务...
                      </p>
                    ) : null}
                  </div>
                </motion.div>
              )}
              </AnimatePresence>

            <div>
              {attachedFiles.length > 0 ? (
                <div className="flex flex-wrap gap-2 px-5 pt-3">
                  {attachedFiles.map((file, index) => (
                    <div
                      key={`${file.name}-${index}`}
                      className="flex items-center gap-1.5 rounded-md border border-border bg-card px-2.5 py-1 text-xs text-foreground"
                    >
                      <Paperclip className="size-3 shrink-0 text-muted-foreground" />
                      <span className="max-w-[120px] truncate">{file.name}</span>
                      <button
                        type="button"
                        onClick={() => handleRemoveFile(index)}
                        className="ml-0.5 text-muted-foreground hover:text-foreground"
                        aria-label={`移除 ${file.name}`}
                      >
                        <XIcon className="size-3" />
                      </button>
                    </div>
                  ))}
                </div>
              ) : null}
              <Textarea
                ref={textareaRef}
                value={input}
                onChange={(event) => {
                  onInputChange(event.target.value);
                }}
                onKeyDown={onKeyDown}
                placeholder={
                  isModelsLoading
                    ? "正在加载模型..."
                    : selectedModel
                      ? "分配一个任务或提问任何问题"
                      : "当前没有可用模型，暂时无法开始会话"
                }
                className="min-h-[88px] resize-none overflow-y-hidden rounded-none border-none bg-transparent px-6 py-5 text-[14px] leading-[22px] shadow-none focus-visible:ring-0"
                disabled={isComposerDisabled}
                style={{ height: "88px" }}
              />
              <div className="flex flex-col gap-2 bg-transparent px-5 pb-3 pt-0 sm:flex-row sm:items-center sm:justify-between">
                <div className="flex flex-wrap items-center gap-2">
                  <ModePicker selected={selectedMode} onSelect={setSelectedMode} placement={pickerPlacement} />
                  <>
                    <input
                      ref={fileInputRef as React.RefObject<HTMLInputElement>}
                      type="file"
                      multiple
                      className="hidden"
                      onChange={handleFileSelect}
                      accept="image/*,.pdf,.txt,.md,.csv,.json,.py,.ts,.tsx,.js,.jsx"
                    />
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      onClick={() => fileInputRef.current?.click()}
                      className="size-9 rounded-full border border-transparent text-muted-foreground hover:border-border hover:bg-secondary"
                      title="上传附件"
                    >
                      <Paperclip className="size-3.5" />
                    </Button>
                  </>
                </div>
                <div className="flex flex-wrap items-center justify-between gap-2 sm:justify-end">
                  <ModelPicker
                    models={modelOptions}
                    selected={selectedModel}
                    onSelect={setSelectedModel}
                    isLoading={isModelsLoading}
                    loadError={modelLoadError}
                    onRetry={fetchModels}
                    placement={pickerPlacement}
                  />
                  {isLoading ? (
                    <Button
                      onClick={onStop}
                      size="icon-sm"
                      className="size-9 rounded-full bg-accent text-accent-foreground shadow-none hover:bg-accent-hover"
                      title="停止生成 (Esc)"
                      aria-label="停止生成"
                    >
                      <Square className="size-3.5 fill-current" />
                    </Button>
                  ) : (
                    <Button
                      onClick={handleSubmit}
                      disabled={!input.trim() || isComposerDisabled}
                      size="icon-sm"
                      className="size-9 rounded-full bg-accent text-accent-foreground shadow-none hover:bg-accent-hover"
                      title="发送 (Enter)"
                      aria-label="发送"
                    >
                      <ArrowUp className="size-3.5" />
                    </Button>
                  )}
                </div>
              </div>
            </div>
            </div>
          </div>

          {isEmpty && quickPrompts.length > 0 ? (
            <div className="mt-8 grid gap-5 md:grid-cols-2 xl:grid-cols-3">
              {quickPrompts.map((item) => (
                <button
                  key={item.prompt}
                  type="button"
                  onClick={() => { onQuickPromptSelect?.(item.prompt); }}
                  className="group text-left"
                >
                  <div
                    className="h-[190px] rounded-[26px] border border-border/80 transition-transform duration-200 group-hover:-translate-y-0.5"
                    style={{
                      background: item.gradient,
                      boxShadow: "0 10px 24px rgba(0, 0, 0, 0.06)",
                    }}
                  >
                    <div className="flex h-full flex-col justify-between p-5">
                      <span className="inline-flex w-fit rounded-full border border-black/6 bg-white/82 px-2.5 py-1 text-[11px] text-foreground/70">
                        {item.tag}
                      </span>
                      <div className="max-w-[220px]">
                        <p className="text-[22px] leading-tight font-semibold text-foreground/90">
                          {item.title}
                        </p>
                        <p className="mt-2 text-[13px] leading-5 text-foreground/70">
                          {item.subtitle}
                        </p>
                      </div>
                    </div>
                  </div>
                  <div className="mt-3 px-1">
                    <p className="text-[16px] font-medium tracking-[-0.02em] text-foreground">
                      {item.title}
                    </p>
                    <p className="mt-1 text-[14px] text-muted-foreground">{item.subtitle}</p>
                    <div className="mt-2 flex items-center gap-2 text-[12px] text-muted-foreground">
                      <span className="rounded-full bg-secondary px-2.5 py-1">{item.tag}</span>
                      <span>{item.uses}</span>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
