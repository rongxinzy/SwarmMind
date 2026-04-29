import type { ChangeEvent, KeyboardEvent, RefObject } from "react";
import React from "react";
import { AnimatePresence, motion } from "framer-motion";
import { ArrowUp, Check, Copy, Loader2, Paperclip, XIcon } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { ModePicker, ModelPicker } from "@/components/workspace/chat-controls";
import type { ChatMessage, ConversationMode, RuntimeModelOption, RuntimeState, StreamStatus, StreamStep } from "@/core/chat/types";
import type { ChatError } from "@/core/chat/types";
import { MODE_BADGE_TOKENS } from "@/core/chat/mode-config";
import { cn } from "@/lib/utils";

interface ChatComposerPanelProps {
  attachedFiles: File[];
  error: ChatError | null;
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
  streamStatus?: StreamStatus;
  streamStep?: StreamStep | null;
  streamLabel?: string | null;
}

function streamStatusText(mode: ConversationMode, status: StreamStatus, step: StreamStep | null, label: string | null): string {
  const token = MODE_BADGE_TOKENS[mode];
  if (status === "thinking") {
    if (label) return label;
    if (mode === "pro") return "多步规划中…";
    if (mode === "ultra") return "深度推理与协作中…";
    if (mode === "thinking") return "深入分析中…";
    return token.streamLabel;
  }
  if (status === "running") {
    if (mode === "pro" && step) {
      return step.totalSteps
        ? `步骤执行中…（第 ${step.step} / ${step.totalSteps} 步）`
        : "步骤执行中…";
    }
    if (mode === "ultra") return "深度推理与协作中…";
    if (mode === "thinking") return "深入分析中…";
    return token.streamLabel;
  }
  if (status === "clarification") return "等待澄清…";
  if (status === "artifact") return "生成产物中…";
  return token.streamLabel;
}

function streamBadgeTone(status: StreamStatus) {
  if (status === "thinking") return "border-accent-border bg-accent-soft text-accent";
  if (status === "running" || status === "artifact") return "border-[var(--status-running-border)] bg-[var(--status-running-bg)] text-[var(--status-running)]";
  if (status === "clarification") return "border-[var(--status-approval-border)] bg-[var(--status-approval-bg)] text-[var(--status-approval)]";
  return "border-[var(--status-draft-border)] bg-[var(--status-draft-bg)] text-[var(--status-draft)]";
}

function streamBadgeLabel(status: StreamStatus) {
  if (status === "thinking") return "思考中";
  if (status === "running") return "执行中";
  if (status === "clarification") return "等待澄清";
  if (status === "artifact") return "生成产物";
  return "待机";
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
  streamStatus,
  streamStep,
  streamLabel,
}: ChatComposerPanelProps) {
  const modeToken = MODE_BADGE_TOKENS[selectedMode];
  const ModeIcon = modeToken.icon;
  const showStatusBar = isLoading || streamStatus || (runtime.phase !== "idle" && runtime.phase !== "completed") || error;

  return (
    <div
      className="sticky bottom-0 z-20"
      style={{
        background:
          "linear-gradient(to top, var(--codex-bg) 0%, var(--codex-bg) 85%, transparent 100%)",
      }}
    >
      <div className="relative border-t border-border/50 bg-background">
        <div className="mx-auto w-full max-w-[760px] px-6 pb-5 pt-2.5">
          <div
            className="rounded-xl border border-border bg-card transition-all duration-200 focus-within:border-accent"
            style={{ boxShadow: "var(--shadow-xs)" }}
          >
            <AnimatePresence>
              {showStatusBar ? (
                <motion.div
                  key="status-bar"
                  initial={{ opacity: 0, y: -6 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -4 }}
                  transition={{ duration: 0.2, ease: [0.16, 1, 0.3, 1] }}
                  className="min-h-[40px] border-b border-border bg-surface-hover px-5 py-2.5"
                  aria-live="polite"
                >
                  <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                    <div className="flex items-center gap-2.5">
                      <span
                        className={cn(
                          "flex size-6 items-center justify-center rounded-md border",
                          modeToken.accent,
                        )}
                      >
                        <ModeIcon className="size-3" />
                      </span>
                      <p className="text-[13px] text-muted-foreground">
                        {error && !isLoading
                          ? error.message
                          : streamStatusText(selectedMode, streamStatus ?? null, streamStep ?? null, streamLabel ?? null)}
                      </p>
                      {isLoading && (
                        <Loader2 className="size-3.5 animate-spin text-muted-foreground" />
                      )}
                    </div>
                    <Badge
                      variant="outline"
                      className={cn(
                        "text-[11px]",
                        error && !isLoading
                          ? "status-pill-blocked"
                          : streamBadgeTone(streamStatus ?? null),
                      )}
                    >
                      {error && !isLoading
                        ? "失败"
                        : streamBadgeLabel(streamStatus ?? null)}
                    </Badge>
                  </div>
                </motion.div>
              ) : null}
            </AnimatePresence>

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
                className="min-h-[100px] resize-none border-none bg-card px-5 py-4 text-[14px] leading-[22px] focus-visible:ring-0"
                disabled={isComposerDisabled}
              />
              <div className="flex flex-col gap-2 border-t border-border bg-surface-hover/70 px-4 py-2.5 sm:flex-row sm:items-center sm:justify-between">
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
                      className="size-10 rounded-lg border border-transparent text-muted-foreground hover:border-border hover:bg-card"
                      title="上传附件"
                    >
                      <Paperclip className="size-4" />
                    </Button>
                  </>
                  {lastAssistantMessage ? (
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      className="size-10 rounded-lg border border-transparent text-muted-foreground hover:border-border hover:bg-card"
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
                    className="size-10 rounded-md bg-accent text-accent-foreground shadow-none hover:bg-accent-hover"
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
