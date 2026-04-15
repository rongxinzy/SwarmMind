import type { ChangeEvent, KeyboardEvent, RefObject } from "react";
import React from "react";
import { AnimatePresence, motion } from "framer-motion";
import { ArrowUp, Check, Copy, Loader2, Paperclip, XIcon } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { ModePicker, ModelPicker } from "@/components/workspace/chat-controls";
import type { ChatMessage, ConversationMode, RuntimeModelOption, RuntimeState } from "@/core/chat/types";
import { cn } from "@/lib/utils";

interface ChatComposerPanelProps {
  attachedFiles: File[];
  error: string | null;
  fetchModels: () => void;
  fileInputRef: RefObject<HTMLInputElement | null>;
  handleFileSelect: (event: ChangeEvent<HTMLInputElement>) => void;
  handleRemoveFile: (index: number) => void;
  handleSubmit: () => void;
  input: string;
  isComposerDisabled: boolean;
  isLoading: boolean;
  isModelsLoading: boolean;
  lastAssistantMessage?: ChatMessage;
  modelLoadError: string | null;
  modelOptions: RuntimeModelOption[];
  onInputChange: (value: string) => void;
  onKeyDown: (event: KeyboardEvent<HTMLTextAreaElement>) => void;
  runtime: RuntimeState;
  selectedMode: ConversationMode;
  selectedModel: string;
  setSelectedMode: (mode: ConversationMode) => void;
  setSelectedModel: (model: string) => void;
}

function statusTone(phase: RuntimeState["phase"]) {
  if (phase === "error") return "status-pill-blocked";
  if (phase === "completed") return "status-pill-done";
  if (phase === "routing" || phase === "running" || phase === "accepted") {
    return "status-pill-running";
  }
  return "status-pill-draft";
}

function statusLabel(phase: RuntimeState["phase"]) {
  if (phase === "accepted") return "已提交";
  if (phase === "routing" || phase === "running") return "生成中";
  if (phase === "completed") return "已完成";
  if (phase === "error") return "失败";
  return "待开始";
}

export function ChatComposerPanel({
  attachedFiles,
  error,
  fetchModels,
  fileInputRef,
  handleFileSelect,
  handleRemoveFile,
  handleSubmit,
  input,
  isComposerDisabled,
  isLoading,
  isModelsLoading,
  lastAssistantMessage,
  modelLoadError,
  modelOptions,
  onInputChange,
  onKeyDown,
  runtime,
  selectedMode,
  selectedModel,
  setSelectedMode,
  setSelectedModel,
}: ChatComposerPanelProps) {
  return (
    <div
      className="sticky bottom-0 z-20"
      style={{
        background:
          "linear-gradient(to top, var(--warm-paper) 0%, var(--warm-paper) 85%, transparent 100%)",
      }}
    >
      <div className="relative border-t border-[var(--warm-border)]/50 bg-[var(--warm-paper)]">
        <div className="mx-auto w-full max-w-[760px] px-6 pb-5 pt-2.5">
          <div
            className="rounded-2xl border border-[var(--warm-border)] bg-[var(--warm-ivory)] transition-all duration-200 focus-within:border-[var(--warm-ring)]"
            style={{ boxShadow: "var(--shadow-whisper)" }}
          >
            {(runtime.phase !== "idle" || error) && (
              <div
                className="border-b border-[var(--warm-border)] bg-[var(--neutral-150)] px-5 py-2.5"
                aria-live="polite"
              >
                <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                  <p className="text-[13px] text-muted-foreground">{error || runtime.label}</p>
                  <Badge variant="outline" className={cn("text-[11px]", statusTone(runtime.phase))}>
                    {statusLabel(runtime.phase)}
                  </Badge>
                </div>
              </div>
            )}

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
                  <div className="flex flex-col gap-1 border-b border-[var(--warm-border)] px-4 py-2">
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
                              ? "text-[var(--neutral-700)]"
                              : "text-[var(--neutral-500)]",
                          )}
                        >
                          {activity.label}
                        </span>
                        {activity.detail ? (
                          <span className="ml-auto max-w-[120px] shrink-0 truncate text-[var(--neutral-400)]">
                            {activity.detail}
                          </span>
                        ) : null}
                      </div>
                    ))}
                    {runtime.activities.length > 5 ? (
                      <p className="pl-5 text-xs text-[var(--neutral-400)]">
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
                      className="flex items-center gap-1.5 rounded-md border border-[var(--warm-border)] bg-[var(--warm-ivory)] px-2.5 py-1 text-xs text-[var(--neutral-700)]"
                    >
                      <Paperclip className="size-3 shrink-0 text-[var(--neutral-500)]" />
                      <span className="max-w-[120px] truncate">{file.name}</span>
                      <button
                        type="button"
                        onClick={() => handleRemoveFile(index)}
                        className="ml-0.5 text-[var(--neutral-400)] hover:text-[var(--neutral-700)]"
                        aria-label={`移除 ${file.name}`}
                      >
                        <XIcon className="size-3" />
                      </button>
                    </div>
                  ))}
                </div>
              ) : null}
              <Textarea
                value={input}
                onChange={(event) => {
                  onInputChange(event.target.value);
                }}
                onKeyDown={onKeyDown}
                placeholder={
                  isModelsLoading
                    ? "正在加载模型..."
                    : selectedModel
                      ? "输入问题或任务..."
                      : "当前没有可用模型，暂时无法开始会话"
                }
                className="min-h-[100px] resize-none border-none bg-card px-5 py-4 text-[15px] leading-[24px] tracking-[-0.003em] focus-visible:ring-0"
                disabled={isComposerDisabled}
              />
              <div className="flex flex-col gap-2 border-t border-[var(--warm-border)] bg-[var(--neutral-150)]/70 px-4 py-2.5 sm:flex-row sm:items-center sm:justify-between">
                <div className="flex flex-wrap items-center gap-2">
                  <ModePicker selected={selectedMode} onSelect={setSelectedMode} />
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
                      className="size-10 rounded-lg border border-transparent text-[var(--neutral-600)] hover:border-[var(--warm-border)] hover:bg-[var(--warm-ivory)]"
                      title="上传附件"
                    >
                      <Paperclip className="size-4" />
                    </Button>
                  </>
                  {lastAssistantMessage ? (
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      className="size-10 rounded-lg border border-transparent text-[var(--neutral-600)] hover:border-[var(--warm-border)] hover:bg-[var(--warm-ivory)]"
                      onClick={() => navigator.clipboard.writeText(lastAssistantMessage.content)}
                      title="复制回复"
                    >
                      <Copy className="size-4" />
                    </Button>
                  ) : null}
                </div>
                <div className="flex flex-wrap items-center justify-between gap-2 sm:justify-end">
                  <ModelPicker
                    models={modelOptions}
                    selected={selectedModel}
                    onSelect={setSelectedModel}
                    isLoading={isModelsLoading}
                    loadError={modelLoadError}
                    onRetry={fetchModels}
                  />
                  <Button
                    onClick={handleSubmit}
                    disabled={!input.trim() || isComposerDisabled}
                    size="icon-sm"
                    className="size-10 rounded-md shadow-none"
                  >
                    {isLoading ? <Loader2 className="size-4 animate-spin" /> : <ArrowUp className="size-4" />}
                  </Button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
