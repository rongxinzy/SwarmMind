"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Streamdown } from "streamdown";
import "streamdown/styles.css";
import remarkGfm from "remark-gfm";
import { AnimatePresence, motion } from "framer-motion";
import {
  ArrowDown,
  ArrowUp,
  Brain,
  Check,
  ChevronDown,
  Copy,
  GraduationCap,
  Lightbulb,
  Loader2,
  Paperclip,
  Rocket,
  Sparkles,
  Zap,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
// Shimmer now imported from ai-elements/reasoning
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import { Reasoning, ReasoningTrigger, ReasoningContent } from "@/components/ai-elements/reasoning";
import { ArtifactsProvider } from "@/components/workspace/artifacts/context";
import { ClarificationCard } from "@/components/workspace/messages/clarification-card";
import { FilesIcon, XIcon } from "lucide-react";
import { SubtasksProvider, useUpdateSubtask, useSubtaskContext } from "@/core/tasks/context";
import { SubtaskCard } from "@/components/workspace/messages/subtask-card";
import { parseClarificationContent } from "@/core/messages/clarification";

interface V0ChatProps {
  conversationId?: string;
  draftResetToken?: number;
  onConversationCreated?: (id: string) => void;
  onConversationsChange?: (items: ConversationRecord[]) => void;
}

export interface ConversationRecord {
  id: string;
  title: string;
  title_status: "pending" | "generated" | "fallback" | "manual";
  updated_at: string;
  created_at: string;
}

interface StoredMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  created_at?: string;
}

interface RuntimeModelOption {
  name: string;
  provider: string;
  model: string;
  display_name?: string | null;
  description?: string | null;
  supports_vision: boolean;
  is_default: boolean;
}

interface RuntimeModelCatalogResponse {
  models: RuntimeModelOption[];
  default_model?: string | null;
}

interface RuntimeActivity {
  id: string;
  label: string;
  status: "running" | "completed";
  detail?: string;
}

interface RuntimeState {
  phase: "idle" | "accepted" | "routing" | "running" | "completed" | "error";
  label: string;
  activities: RuntimeActivity[];
}

interface StreamEventUserMessage {
  id: string;
  role: "user";
  content: string;
  created_at?: string;
}

interface StreamEventAssistantMessage {
  id: string;
  role: "assistant";
  content: string;
  created_at?: string;
}

type StreamEvent =
  | { type: "status"; phase: RuntimeState["phase"]; label: string }
  | { type: "user_message"; message: StreamEventUserMessage }
  | { type: "thinking"; message_id: string; content: string }
  | { type: "assistant_message"; message_id: string; content: string }
  | { type: "assistant_final"; message: StreamEventAssistantMessage }
  | {
      type: "team_activity";
      activity: {
        id: string;
        label: string;
        status: RuntimeActivity["status"];
        detail?: string | null;
      };
    }
  // Task events for SubtaskCard (DeerFlow compatible)
  | { type: "task_started"; task: { id: string; description: string; status: "in_progress" } }
  | { type: "task_running"; task: { id: string; message?: unknown } }
  | { type: "task_completed"; task: { id: string; result?: string; status: "completed" } }
  | { type: "task_failed"; task: { id: string; error?: string; status: "failed" } }
  // Clarification request from AI
  | { type: "clarification_request"; clarification: { id: string; content: string } }
  | {
      type: "title";
      conversation: ConversationRecord;
    }
  | { type: "done" };

type ChatMessage = StoredMessage & {
  pendingPersist?: boolean;
  isStreaming?: boolean;
  thinking?: string;
  isReasoningStreaming?: boolean;
};

type ConversationMode = "flash" | "thinking" | "pro" | "ultra";

const QUICK_PROMPTS = [
  "帮我整理本周项目进展，输出 3 条重点结论。",
  "生成一版 CRM MVP 范围说明，控制在一页内。",
  "把下面的会议讨论改写成正式纪要。",
  "总结当前续费风险，并给出 3 条行动建议。",
];

const MODEL_FETCH_RETRY_COUNT = 3;
const MODEL_FETCH_RETRY_DELAY_MS = 400;

const MODE_OPTIONS: Array<{
  id: ConversationMode;
  label: string;
  description: string;
  accentClassName: string;
  icon: typeof Zap;
}> = [
  {
    id: "flash",
    label: "Flash",
    description: "最快回复，不展开推理",
    accentClassName: "border-[#d2dce3] bg-[#f4f7f9] text-[#46586b]",
    icon: Zap,
  },
  {
    id: "thinking",
    label: "Thinking",
    description: "保留推理过程，单轮深入分析",
    accentClassName: "border-[#ddd7e4] bg-[#f6f3f8] text-[#5c516b]",
    icon: Lightbulb,
  },
  {
    id: "pro",
    label: "Pro",
    description: "先规划再执行",
    accentClassName: "border-[#d4ded3] bg-[#f3f6f2] text-[#48604f]",
    icon: GraduationCap,
  },
  {
    id: "ultra",
    label: "Ultra",
    description: "启用完整协作流程",
    accentClassName: "border-[#dfd4c3] bg-[#f8f4ed] text-[#6d5a3e]",
    icon: Rocket,
  },
];

const DEFAULT_MODE: ConversationMode = "flash";
const DEFAULT_MODEL = "";

const streamAnimateOptions = {
  animation: "fadeIn" as const,
  duration: 300,
  stagger: 20,
  sep: "word" as const,
};

const streamingRemarkPlugins = [remarkGfm];
const staticRemarkPlugins = [remarkGfm];

function generateId() {
  return Math.random().toString(36).slice(2, 10);
}

function createEmptyRuntime(): RuntimeState {
  return {
    phase: "idle",
    label: "等待新的输入",
    activities: [],
  };
}

function findActiveAssistantIndex(messages: ChatMessage[]) {
  const reverseIndex = [...messages]
    .reverse()
    .findIndex(
      (message) =>
        message.role === "assistant" &&
        (message.isStreaming || message.isReasoningStreaming),
    );

  if (reverseIndex === -1) {
    return -1;
  }

  return messages.length - 1 - reverseIndex;
}

function sortConversations(items: ConversationRecord[]) {
  return [...items].sort((a, b) => {
    const left = new Date(a.updated_at).getTime();
    const right = new Date(b.updated_at).getTime();
    return right - left;
  });
}

function upsertActivity(
  activities: RuntimeActivity[],
  patch: Partial<RuntimeActivity> & {
    id: string;
    label: string;
    status: RuntimeActivity["status"];
  },
) {
  const index = activities.findIndex((activity) => activity.id === patch.id);
  if (index === -1) {
    return [
      {
        id: patch.id,
        label: patch.label,
        status: patch.status,
        detail: patch.detail,
      },
      ...activities,
    ];
  }

  const next = [...activities];
  next[index] = {
    ...next[index],
    ...patch,
  };
  return next;
}

function statusTone(phase: RuntimeState["phase"]) {
  if (phase === "error") return "status-pill-blocked";
  if (phase === "completed") return "status-pill-done";
  if (phase === "routing" || phase === "running" || phase === "accepted")
    return "status-pill-running";
  return "status-pill-draft";
}

function statusLabel(phase: RuntimeState["phase"]) {
  if (phase === "accepted") return "已提交";
  if (phase === "routing" || phase === "running") return "生成中";
  if (phase === "completed") return "已完成";
  if (phase === "error") return "失败";
  return "待开始";
}

function ModePicker({
  selected,
  onSelect,
}: {
  selected: ConversationMode;
  onSelect: (id: ConversationMode) => void;
}) {
  const [open, setOpen] = useState(false);
  const current =
    MODE_OPTIONS.find((mode) => mode.id === selected) ?? MODE_OPTIONS[0];
  const CurrentIcon = current.icon;

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        aria-label={`当前执行模式：${current.label}`}
        className={cn(
          "group flex min-h-10 items-center gap-2 rounded-md border px-3 py-2 text-left transition-colors hover:border-border focus-visible:border-[#bec8d0] focus-visible:ring-4 focus-visible:ring-[#e7ecef]/80",
          current.accentClassName,
        )}
      >
        <span className="flex size-6 items-center justify-center rounded-md border border-black/5 bg-background">
          <CurrentIcon className="size-3" />
        </span>
        <span className="min-w-0">
          <span className="block text-[10px] leading-4 font-semibold tracking-[0.08em]">
            {current.label}
          </span>
        </span>
        <ChevronDown
          className={cn(
            "size-3 shrink-0 transition-transform duration-200",
            open && "rotate-180",
          )}
        />
      </button>

      <AnimatePresence>
        {open && (
          <>
            <div
              className="fixed inset-0 z-40"
              onClick={() => setOpen(false)}
            />
            <motion.div
              initial={{ opacity: 0, y: 8, scale: 0.97 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 8, scale: 0.97 }}
              transition={{
                type: "spring",
                stiffness: 360,
                damping: 28,
                mass: 0.9,
              }}
              className="absolute bottom-full left-0 z-50 mb-2.5 w-[286px] rounded-[18px] border border-border bg-card p-2"
            >
              <div className="mb-1.5 px-1">
                <p className="text-[10px] uppercase tracking-[0.1em] text-muted-foreground">
                  执行模式
                </p>
                <p className="text-[12px] text-foreground">
                  选择这轮临时会话的执行方式
                </p>
              </div>
              <div className="space-y-1.5">
                {MODE_OPTIONS.map((mode, index) => {
                  const Icon = mode.icon;
                  const isSelected = mode.id === selected;

                  return (
                    <motion.button
                      key={mode.id}
                      type="button"
                      onClick={() => {
                        onSelect(mode.id);
                        setOpen(false);
                      }}
                      initial={{ opacity: 0, y: 6 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: index * 0.03 }}
                      className={cn(
                        "flex w-full items-start gap-2.5 rounded-[14px] border px-3 py-2.5 text-left transition-colors",
                        isSelected
                          ? cn("bg-card", mode.accentClassName)
                          : "border-border bg-background text-foreground hover:border-border hover:bg-secondary",
                      )}
                    >
                      <span
                        className={cn(
                          "mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-md border bg-background",
                          isSelected ? "border-black/5" : "border-border/80",
                        )}
                      >
                        <Icon className="size-3.5" />
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="text-[12px] font-semibold">
                          {mode.label}
                        </span>
                        <span className="mt-0.5 block text-[11px] leading-4 opacity-80">
                          {mode.description}
                        </span>
                      </span>
                    </motion.button>
                  );
                })}
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
}

function ModelPicker({
  models,
  selected,
  onSelect,
  isLoading,
  loadError,
  onRetry,
}: {
  models: RuntimeModelOption[];
  selected: string;
  onSelect: (id: string) => void;
  isLoading: boolean;
  loadError: string | null;
  onRetry: () => void;
}) {
  const [open, setOpen] = useState(false);
  const current = models.find((model) => model.name === selected) ?? models[0];
  const currentLabel =
    current?.display_name ||
    current?.name ||
    (isLoading ? "加载模型..." : loadError ? "模型加载失败" : "未配置模型");
  const isDisabled = isLoading || (!loadError && models.length <= 1);

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => {
          if (loadError) {
            onRetry();
            return;
          }
          if (!isDisabled) {
            setOpen((prev) => !prev);
          }
        }}
        disabled={isDisabled}
        title={loadError ?? undefined}
        className="flex min-h-10 items-center gap-2 rounded-md border border-transparent bg-transparent px-3 text-[11px] tracking-[0.08em] text-muted-foreground transition-colors hover:border-border hover:bg-secondary hover:text-foreground focus-visible:border-[#bec8d0] focus-visible:ring-4 focus-visible:ring-[#e7ecef]/80"
      >
        <Sparkles className="size-3.5" />
        <span className="max-w-[140px] truncate">{currentLabel}</span>
      </button>

      <AnimatePresence>
        {open && (
          <>
            <div
              className="fixed inset-0 z-40"
              onClick={() => setOpen(false)}
            />
            <motion.div
              initial={{ opacity: 0, y: 4, scale: 0.96 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 4, scale: 0.96 }}
              transition={{
                type: "spring",
                stiffness: 500,
                damping: 30,
                mass: 0.8,
              }}
              className="absolute bottom-full left-0 z-50 mb-2 w-[220px] overflow-hidden rounded-[16px] border border-border bg-card p-1.5"
            >
              {models.map((model) => (
                <button
                  key={model.name}
                  type="button"
                  onClick={() => {
                    onSelect(model.name);
                    setOpen(false);
                  }}
                  className={cn(
                    "flex min-h-11 w-full items-center gap-2 rounded-[14px] px-3 py-2 text-[13px] transition-colors",
                    model.name === selected
                      ? "bg-secondary text-foreground font-medium"
                      : "text-muted-foreground hover:bg-secondary hover:text-foreground",
                  )}
                >
                  <Sparkles className="size-3.5 shrink-0" />
                  <span className="truncate">
                    {model.display_name || model.name}
                  </span>
                </button>
              ))}
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
}

function MessageBubble({
  message,
  isMessageStreaming = false,
}: {
  message: ChatMessage;
  isMessageStreaming?: boolean;
}) {
  const isUser = message.role === "user";
  const hasCodeBlock = !isUser && message.content.includes("```");
  const shouldShowMessageCopy =
    message.content.trim().length > 0 && (isUser || !hasCodeBlock);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!copied) {
      return;
    }

    const timer = window.setTimeout(() => setCopied(false), 2000);
    return () => window.clearTimeout(timer);
  }, [copied]);

  const handleCopy = useCallback(async () => {
    if (!message.content.trim()) {
      return;
    }

    try {
      await navigator.clipboard.writeText(message.content);
      setCopied(true);
    } catch (error) {
      console.error("Failed to copy message content:", error);
    }
  }, [message.content]);

  return (
    <div
      className={cn(
        "group flex w-full",
        isUser ? "justify-end" : "justify-start md:pr-8",
      )}
    >
      <div
        className={cn(
          "relative max-w-[90%]",
          isUser
            ? "rounded-[20px] border user-bubble px-[18px] py-[13px] text-foreground"
            : "px-1 py-1 md:px-2",
        )}
      >
        {shouldShowMessageCopy ? (
          <div
            className={cn(
              "absolute transition-opacity md:opacity-0 md:group-hover:opacity-100 md:group-focus-within:opacity-100",
              isUser
                ? "-right-1 -top-1 opacity-100"
                : "right-2 top-1 opacity-80",
            )}
          >
            <Button
              type="button"
              variant="ghost"
              size="icon-xs"
              onClick={() => {
                void handleCopy();
              }}
              className={cn(
                "h-8 w-8 rounded-[10px] text-muted-foreground md:h-7 md:w-7",
                isUser
                  ? "border border-border bg-card hover:bg-card hover:text-foreground"
                  : "border border-transparent bg-background hover:border-border hover:bg-secondary hover:text-foreground",
              )}
              title={copied ? "已复制" : "复制消息"}
            >
              {copied ? (
                <Check className="size-3 text-[#0d6b4b]" />
              ) : (
                <Copy className="size-3" />
              )}
            </Button>
          </div>
        ) : null}

        {!isUser && message.thinking ? (
          <Reasoning
            isStreaming={message.isReasoningStreaming}
            defaultOpen={true}
            className="mb-4"
          >
            <ReasoningTrigger />
            <ReasoningContent>{message.thinking}</ReasoningContent>
          </Reasoning>
        ) : null}

        {message.content ? (
          isUser ? (
            <div className="whitespace-pre-wrap font-[var(--font-body)] text-[14px] leading-[22px]">
              {message.content}
            </div>
          ) : (
            <div className="assistant-markdown prose prose-sm max-w-none px-[12px] py-1 font-[var(--font-body)] text-[14px] leading-[24px] tracking-[-0.003em] text-foreground prose-headings:font-sans prose-pre:my-0 prose-pre:mx-0 prose-pre:rounded-none prose-pre:border-0 prose-pre:bg-transparent prose-pre:p-0 prose-code:font-mono">
              <Streamdown
                mode={isMessageStreaming ? "streaming" : "static"}
                remarkPlugins={
                  isMessageStreaming
                    ? streamingRemarkPlugins
                    : staticRemarkPlugins
                }
                animated={isMessageStreaming ? streamAnimateOptions : false}
              >
                {message.content}
              </Streamdown>
            </div>
          )
        ) : (
          <div className="flex items-center gap-2 text-[14px] leading-[22px] text-muted-foreground">
            <StreamingDots />
            正在整理回复
          </div>
        )}
      </div>
    </div>
  );
}

function StreamingDots({ className }: { className?: string }) {
  return (
    <div
      className={cn("inline-flex items-center", className)}
      aria-hidden="true"
    >
      {[0, 1, 2].map((index) => (
        <span
          key={index}
          className="chat-stream-dot"
          style={{ animationDelay: `${index * 0.16}s` }}
        />
      ))}
    </div>
  );
}

function MessageListSkeleton() {
  return (
    <div className="mx-auto flex w-full max-w-[760px] flex-col gap-7 px-6 py-6">
      <div className="flex justify-end">
        <div className="w-full max-w-[420px] space-y-2">
          <div className="skeleton-line h-4 rounded-full" />
          <div className="skeleton-line ml-auto h-4 w-[72%] rounded-full" />
        </div>
      </div>

      <div className="flex justify-start">
        <div className="w-full max-w-[560px] space-y-2">
          <div className="skeleton-line h-4 rounded-full" />
          <div className="skeleton-line h-4 w-[94%] rounded-full" />
          <div className="skeleton-line h-4 w-[68%] rounded-full" />
        </div>
      </div>

      <div className="flex justify-start">
        <div className="w-full max-w-[520px] rounded-2xl border border-border/70 bg-[#f7f6f3] px-4 py-4">
          <div className="space-y-2">
            <div className="skeleton-line h-3.5 w-[120px] rounded-full" />
            <div className="skeleton-line h-4 rounded-full" />
            <div className="skeleton-line h-4 w-[88%] rounded-full" />
            <div className="skeleton-line h-4 w-[54%] rounded-full" />
          </div>
        </div>
      </div>
    </div>
  );
}

// Internal component that uses useUpdateSubtask (must be inside SubtasksProvider)
function V0ChatInner({
  conversationId,
  draftResetToken,
  onConversationCreated,
  onConversationsChange,
}: V0ChatProps) {
  const updateSubtask = useUpdateSubtask();
  const { tasks } = useSubtaskContext();
  const [conversations, setConversations] = useState<ConversationRecord[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [runtime, setRuntime] = useState<RuntimeState>(createEmptyRuntime());
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [selectedMode, setSelectedMode] =
    useState<ConversationMode>(DEFAULT_MODE);
  const [selectedModel, setSelectedModel] = useState(DEFAULT_MODEL);
  const [defaultModel, setDefaultModel] = useState(DEFAULT_MODEL);
  const [modelOptions, setModelOptions] = useState<RuntimeModelOption[]>([]);
  const [isModelsLoading, setIsModelsLoading] = useState(true);
  const [isConversationLoading, setIsConversationLoading] = useState(false);
  const [modelLoadError, setModelLoadError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [currentConversationId, setCurrentConversationId] = useState<
    string | undefined
  >(undefined);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const shouldStickToBottomRef = useRef(true);
  const [showScrollToLatest, setShowScrollToLatest] = useState(false);
  
  // Clarification request state
  const [pendingClarification, setPendingClarification] = useState<
    { id: string; content: string } | null
  >(null);

  const resetDraftState = useCallback(() => {
    setCurrentConversationId(undefined);
    setMessages([]);
    setRuntime(createEmptyRuntime());
    setIsConversationLoading(false);
    setError(null);
    setInput("");
    setSelectedMode(DEFAULT_MODE);
    setPendingClarification(null);
    setSelectedModel(defaultModel);
    shouldStickToBottomRef.current = true;
    setShowScrollToLatest(false);
  }, [defaultModel]);

  const syncScrollState = useCallback(() => {
    const container = scrollContainerRef.current;
    if (!container) {
      return;
    }

    const distanceToBottom =
      container.scrollHeight - container.scrollTop - container.clientHeight;
    const isNearBottom = distanceToBottom <= 72;
    shouldStickToBottomRef.current = isNearBottom;
    setShowScrollToLatest(!isNearBottom);
  }, []);

  const scrollToLatest = useCallback((behavior: ScrollBehavior = "smooth") => {
    const container = scrollContainerRef.current;
    if (!container) {
      return;
    }

    container.scrollTo({
      top: container.scrollHeight,
      behavior,
    });
    shouldStickToBottomRef.current = true;
    setShowScrollToLatest(false);
  }, []);

  const fetchModels = useCallback(async () => {
    setIsModelsLoading(true);
    setModelLoadError(null);

    for (let attempt = 1; attempt <= MODEL_FETCH_RETRY_COUNT; attempt += 1) {
      try {
        const response = await fetch("/models");
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }
        const data = (await response.json()) as RuntimeModelCatalogResponse;
        const nextModels = data.models ?? [];
        const nextDefaultModel =
          data.default_model ?? nextModels[0]?.name ?? DEFAULT_MODEL;
        setModelOptions(nextModels);
        setDefaultModel(nextDefaultModel);
        setSelectedModel((current) => {
          if (current && nextModels.some((model) => model.name === current)) {
            return current;
          }
          return nextDefaultModel;
        });
        setModelLoadError(
          nextModels.length === 0 ? "当前未分配可用模型" : null,
        );
        setIsModelsLoading(false);
        return;
      } catch (requestError) {
        if (attempt === MODEL_FETCH_RETRY_COUNT) {
          console.error("Failed to fetch runtime models:", requestError);
          setModelOptions([]);
          setDefaultModel(DEFAULT_MODEL);
          setSelectedModel(DEFAULT_MODEL);
          setModelLoadError(
            requestError instanceof Error
              ? requestError.message
              : "模型加载失败",
          );
          setIsModelsLoading(false);
          return;
        }

        await new Promise((resolve) =>
          window.setTimeout(resolve, MODEL_FETCH_RETRY_DELAY_MS * attempt),
        );
      }
    }
  }, []);

  const fetchConversations = useCallback(async () => {
    try {
      const response = await fetch("/conversations");
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      const data = await response.json();
      setConversations(sortConversations(data.items));
    } catch (requestError) {
      console.error("Failed to fetch conversations:", requestError);
    }
  }, []);

  const loadMessages = useCallback(async (nextConversationId: string) => {
    setIsConversationLoading(true);
    setMessages([]);
    setRuntime(createEmptyRuntime());
    setError(null);
    shouldStickToBottomRef.current = true;
    setShowScrollToLatest(false);
    setPendingClarification(null);

    try {
      const response = await fetch(
        `/conversations/${nextConversationId}/messages`,
      );
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      const data = await response.json();
      setMessages(
        data.items.map((message: StoredMessage) => ({
          id: message.id,
          role: message.role,
          content: message.content,
          created_at: message.created_at,
        })),
      );
    } catch (requestError) {
      console.error("Failed to load messages:", requestError);
      setError(
        requestError instanceof Error ? requestError.message : "加载会话失败",
      );
    } finally {
      setIsConversationLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchModels();
  }, [fetchModels]);

  useEffect(() => {
    if (!modelLoadError || modelOptions.length > 0) {
      return;
    }

    const retryTimer = window.setTimeout(() => {
      void fetchModels();
    }, 3000);

    return () => window.clearTimeout(retryTimer);
  }, [fetchModels, modelLoadError, modelOptions.length]);

  useEffect(() => {
    void fetchConversations();
  }, [fetchConversations]);

  useEffect(() => {
    onConversationsChange?.(conversations);
  }, [conversations, onConversationsChange]);

  useEffect(() => {
    if (conversationId) {
      if (conversationId !== currentConversationId) {
        setCurrentConversationId(conversationId);
        void loadMessages(conversationId);
      }
      return;
    }

    resetDraftState();
  }, [
    conversationId,
    currentConversationId,
    loadMessages,
    resetDraftState,
    draftResetToken,
  ]);

  useEffect(() => {
    if (!shouldStickToBottomRef.current) {
      const rafId = window.requestAnimationFrame(() => {
        syncScrollState();
      });
      return () => window.cancelAnimationFrame(rafId);
    }

    const rafId = window.requestAnimationFrame(() => {
      scrollToLatest(messages.length > 0 ? "smooth" : "auto");
    });
    return () => window.cancelAnimationFrame(rafId);
  }, [messages, runtime, scrollToLatest, syncScrollState]);

  useEffect(() => {
    if (selectedModel) {
      return;
    }
    if (!defaultModel) {
      return;
    }
    setSelectedModel(defaultModel);
  }, [defaultModel, selectedModel]);

  const lastAssistantMessage = useMemo(
    () =>
      [...messages]
        .reverse()
        .find(
          (message) =>
            message.role === "assistant" && message.content.trim().length > 0,
        ),
    [messages],
  );

  const createConversation = useCallback(
    async (goal: string) => {
      const response = await fetch("/conversations", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ goal }),
      });
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const record = (await response.json()) as ConversationRecord;
      setConversations((previous) =>
        sortConversations([
          record,
          ...previous.filter((item) => item.id !== record.id),
        ]),
      );
      setCurrentConversationId(record.id);
      onConversationCreated?.(record.id);
      return record.id;
    },
    [onConversationCreated],
  );

  const handleStreamEvent = useCallback((event: StreamEvent) => {
    switch (event.type) {
      case "status":
        setRuntime((previous) => ({
          ...previous,
          phase: event.phase,
          label: event.label,
        }));
        if (event.phase === "completed" || event.phase === "error") {
          setIsLoading(false);
          setMessages((previous) =>
            previous.map((message) =>
              message.role === "assistant"
                ? {
                    ...message,
                    isStreaming: false,
                    isReasoningStreaming: false,
                  }
                : message,
            ),
          );
        }
        return;

      case "user_message":
        setMessages((previous) => {
          const pendingIndex = [...previous]
            .reverse()
            .findIndex(
              (message) => message.role === "user" && message.pendingPersist,
            );
          if (pendingIndex === -1) {
            return [
              ...previous,
              {
                id: event.message.id,
                role: "user",
                content: event.message.content,
                created_at: event.message.created_at,
              },
            ];
          }

          const actualIndex = previous.length - 1 - pendingIndex;
          const next = [...previous];
          next[actualIndex] = {
            ...next[actualIndex],
            id: event.message.id,
            pendingPersist: false,
            created_at: event.message.created_at,
          };
          return next;
        });
        return;

      case "thinking":
        setMessages((previous) => {
          const exactIndex = previous.findIndex(
            (message) => message.id === event.message_id,
          );
          if (exactIndex !== -1) {
            const next = [...previous];
            next[exactIndex] = {
              ...next[exactIndex],
              thinking: event.content,
              isReasoningStreaming: true,
            };
            return next;
          }

          const activeAssistantIndex = findActiveAssistantIndex(previous);
          if (activeAssistantIndex !== -1) {
            const next = [...previous];
            next[activeAssistantIndex] = {
              ...next[activeAssistantIndex],
              id: event.message_id,
              thinking: event.content,
              isReasoningStreaming: true,
            };
            return next;
          }

          return [
            ...previous,
            {
              id: event.message_id,
              role: "assistant",
              content: "",
              thinking: event.content,
              isStreaming: false,
              isReasoningStreaming: true,
            },
          ];
        });
        return;

      case "assistant_message":
        setMessages((previous) => {
          const index = previous.findIndex(
            (message) => message.id === event.message_id,
          );
          if (index !== -1) {
            const next = [...previous];
            next[index] = {
              ...next[index],
              content: event.content,
              isStreaming: true,
              // Thinking ends when assistant message starts streaming
              isReasoningStreaming: false,
            };
            return next;
          }

          const activeAssistantIndex = findActiveAssistantIndex(previous);
          if (activeAssistantIndex !== -1) {
            const next = [...previous];
            next[activeAssistantIndex] = {
              ...next[activeAssistantIndex],
              id: event.message_id,
              content: event.content,
              isStreaming: true,
              // Thinking ends when assistant message starts streaming
              isReasoningStreaming: false,
            };
            return next;
          }

          return [
            ...previous,
            {
              id: event.message_id,
              role: "assistant",
              content: event.content,
              isStreaming: true,
              isReasoningStreaming: false,
            },
          ];
        });
        return;

      case "assistant_final":
        setIsLoading(false);
        setRuntime((previous) => ({
          ...previous,
          phase: "completed",
          label: "本轮会话已完成",
        }));
        setMessages((previous) => {
          const exactIndex = previous.findIndex(
            (message) => message.id === event.message.id,
          );
          if (exactIndex !== -1) {
            const next = [...previous];
            next[exactIndex] = {
              ...next[exactIndex],
              ...event.message,
              isStreaming: false,
              isReasoningStreaming: false,
            };
            return next;
          }

          const activeAssistantIndex = findActiveAssistantIndex(previous);
          if (activeAssistantIndex !== -1) {
            const next = [...previous];
            // Update the primary active message with the final message data
            next[activeAssistantIndex] = {
              ...next[activeAssistantIndex],
              ...event.message,
              isStreaming: false,
              isReasoningStreaming: false,
            };
            // Also clear streaming state from any other assistant messages
            // (Ultra mode can create multiple messages with thinking state)
            for (let i = 0; i < next.length; i++) {
              if (
                i !== activeAssistantIndex &&
                next[i].role === "assistant" &&
                (next[i].isStreaming || next[i].isReasoningStreaming)
              ) {
                next[i] = {
                  ...next[i],
                  isStreaming: false,
                  isReasoningStreaming: false,
                };
              }
            }
            return next;
          }

          return [
            ...previous,
            {
              ...event.message,
              isStreaming: false,
              isReasoningStreaming: false,
            },
          ];
        });
        return;

      case "team_activity":
        setRuntime((previous) => ({
          ...previous,
          activities: upsertActivity(previous.activities, {
            id: event.activity.id,
            label: event.activity.label,
            status: event.activity.status,
            detail: event.activity.detail ?? undefined,
          }),
        }));
        return;

      case "title":
        setConversations((previous) =>
          sortConversations([
            event.conversation,
            ...previous.filter(
              (conversation) => conversation.id !== event.conversation.id,
            ),
          ]),
        );
        return;

      // New task events for SubtaskCard
      case "task_started":
        updateSubtask({
          id: event.task.id,
          description: event.task.description,
          status: "in_progress",
          subagent_type: "general-purpose",
          prompt: "",
        });
        return;

      case "task_running":
        updateSubtask({
          id: event.task.id,
          latestMessage: event.task.message as Record<string, unknown> as never,
        });
        return;

      case "task_completed":
        updateSubtask({
          id: event.task.id,
          status: "completed",
          result: event.task.result,
        });
        return;

      case "task_failed":
        updateSubtask({
          id: event.task.id,
          status: "failed",
          error: event.task.error,
        });
        return;

      case "clarification_request":
        setPendingClarification({
          id: event.clarification.id,
          content: event.clarification.content,
        });
        return;

      case "done":
        setIsLoading(false);
        setMessages((previous) =>
          previous.map((message) =>
            message.role === "assistant"
              ? {
                  ...message,
                  isStreaming: false,
                  isReasoningStreaming: false,
                }
              : message,
          ),
        );
    }
  }, [updateSubtask]);

  const streamConversation = useCallback(
    async (
      nextConversationId: string,
      text: string,
      mode: ConversationMode,
      modelName: string,
    ) => {
      const payload: {
        content: string;
        mode: ConversationMode;
        model_name?: string;
      } = {
        content: text,
        mode,
      };
      if (modelName) {
        payload.model_name = modelName;
      }

      const response = await fetch(
        `/conversations/${nextConversationId}/messages/stream`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        },
      );

      if (!response.ok || !response.body) {
        throw new Error(`HTTP ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        let lineBreakIndex = buffer.indexOf("\n");
        while (lineBreakIndex >= 0) {
          const rawLine = buffer.slice(0, lineBreakIndex).trim();
          buffer = buffer.slice(lineBreakIndex + 1);

          if (rawLine) {
            handleStreamEvent(JSON.parse(rawLine) as StreamEvent);
          }

          lineBreakIndex = buffer.indexOf("\n");
        }
      }

      const lastLine = buffer.trim();
      if (lastLine) {
        handleStreamEvent(JSON.parse(lastLine) as StreamEvent);
      }
    },
    [handleStreamEvent],
  );

  const handleSubmit = useCallback(
    async (prompt?: string) => {
      const text = (prompt ?? input).trim();
      if (!text || isLoading) return;
      if (!selectedModel) {
        setError(modelLoadError ?? "当前未分配可用模型，无法发起会话");
        return;
      }

      if (!prompt) setInput("");

      setError(null);
      setIsLoading(true);
      setPendingClarification(null); // Clear any pending clarification when sending new message
      shouldStickToBottomRef.current = true;
      setShowScrollToLatest(false);
      setRuntime({
        ...createEmptyRuntime(),
        phase: "accepted",
        label: "消息已提交，正在准备回复",
      });

      setMessages((previous) => [
        ...previous,
        {
          id: `temp-user-${generateId()}`,
          role: "user",
          content: text,
          pendingPersist: true,
        },
      ]);

      try {
        const nextConversationId =
          currentConversationId ??
          (await createConversation(text.slice(0, 60)));
        await streamConversation(
          nextConversationId,
          text,
          selectedMode,
          selectedModel,
        );
        await fetchConversations();
      } catch (requestError) {
        setIsLoading(false);
        const message =
          requestError instanceof Error
            ? requestError.message
            : "发送消息时发生未知错误";
        setError(message);
        setRuntime((previous) => ({
          ...previous,
          phase: "error",
          label: `会话执行失败：${message}`,
        }));
      }
    },
    [
      createConversation,
      currentConversationId,
      fetchConversations,
      input,
      isLoading,
      modelLoadError,
      selectedMode,
      selectedModel,
      streamConversation,
    ],
  );

  const isEmpty = messages.length === 0 && !isLoading && !isConversationLoading;
  const isComposerDisabled = isLoading || isModelsLoading || !selectedModel;

  // Handle clarification response from user
  const handleClarificationRespond = useCallback(
    async (response: string, toolCallId: string) => {
      if (!currentConversationId) return;

      try {
        // Send clarification response to backend
        const res = await fetch(
          `/conversations/${currentConversationId}/clarification`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              tool_call_id: toolCallId,
              response,
            }),
          }
        );

        if (!res.ok) {
          throw new Error(`HTTP ${res.status}`);
        }

        // After sending clarification response, trigger a new message stream
        // to resume the conversation
        setIsLoading(true);
        setRuntime((prev) => ({
          ...prev,
          phase: "running",
          label: "正在继续处理...",
        }));

        // Resume streaming - the backend will pick up from where it left off
        await streamConversation(
          currentConversationId,
          response,
          selectedMode,
          selectedModel
        );
      } catch (err) {
        console.error("Failed to send clarification response:", err);
        setError(
          err instanceof Error ? err.message : "发送回复失败"
        );
        setIsLoading(false);
      }
    },
    [currentConversationId, selectedMode, selectedModel, streamConversation]
  );

  // Artifacts state (simplified from DeerFlow)
  const [artifacts, _setArtifacts] = useState<string[]>([]);
  const [selectedArtifact, setSelectedArtifact] = useState<string | null>(null);
  const [artifactsOpen, setArtifactsOpen] = useState(false);

  return (
    <ArtifactsProvider>
      <ChatLayout
        conversationId={currentConversationId}
        artifacts={artifacts}
        selectedArtifact={selectedArtifact}
        onSelectArtifact={setSelectedArtifact}
        artifactsOpen={artifactsOpen}
        setArtifactsOpen={setArtifactsOpen}
      >
        <div className="relative flex min-h-0 flex-1 flex-col overflow-hidden bg-background">
      {/* Scrollable area: messages OR empty-state */}
      <div className="relative flex min-h-0 flex-1 flex-col">
        <div
          ref={scrollContainerRef}
          onScroll={syncScrollState}
          className="flex min-h-0 flex-1 flex-col overflow-y-auto overscroll-contain"
        >
          {isConversationLoading ? (
            <MessageListSkeleton />
          ) : isEmpty ? (
            <div className="flex flex-1 flex-col px-6 pt-14">
              <div className="mx-auto w-full max-w-[560px]">
                <motion.div
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
                  className="mb-7"
                >
                  <div className="inline-flex size-9 items-center justify-center rounded-lg border border-border bg-card text-muted-foreground">
                    <Sparkles className="size-4 text-[#6c6259]" />
                  </div>
                  <p className="mt-5 text-[11px] uppercase tracking-[0.08em] text-muted-foreground">
                    Exploratory Session
                  </p>
                  <h2 className="mt-2 text-[28px] leading-[36px] font-semibold tracking-[-0.02em] text-foreground">
                    临时会话
                  </h2>
                  <p className="mt-2 max-w-[440px] text-[14px] leading-[22px] text-muted-foreground">
                    用一个明确任务开始探索。首次发送成功后，系统才会创建正式会话记录。
                  </p>
                </motion.div>

                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 0.15, duration: 0.2 }}
                  className="mb-3 flex items-center gap-2"
                >
                  <p className="text-[12px] font-medium uppercase tracking-[0.08em] text-muted-foreground">
                    快速开始
                  </p>
                  <span className="h-px flex-1 bg-border/50" />
                </motion.div>
                <div className="grid gap-2.5 sm:grid-cols-2">
                  {[
                    { icon: Rocket, prompt: QUICK_PROMPTS[0] },
                    { icon: Lightbulb, prompt: QUICK_PROMPTS[1] },
                    { icon: Brain, prompt: QUICK_PROMPTS[2] },
                    { icon: Sparkles, prompt: QUICK_PROMPTS[3] },
                  ].map(({ icon: Icon, prompt }, i) => (
                    <motion.button
                      key={prompt}
                      initial={{ opacity: 0, y: 12 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{
                        delay: 0.2 + i * 0.06,
                        duration: 0.25,
                        ease: [0.16, 1, 0.3, 1],
                      }}
                      onClick={() => {
                        setInput(prompt);
                        void handleSubmit(prompt);
                      }}
                      className="group flex items-start gap-3 rounded-lg border border-border bg-card px-4 py-3.5 text-left transition-colors hover:border-[#c6cec6] hover:bg-secondary"
                    >
                      <span
                        className={cn(
                          "mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-md border border-black/5 transition-colors",
                          i === 0
                            ? "bg-[#e2e8ee] text-[#49617a]"
                            : i === 1
                              ? "bg-[#ece3d6] text-[#756046]"
                              : i === 2
                                ? "bg-[#eae6ef] text-[#66597c]"
                                : "bg-[#e4ebe4] text-[#4c6554]",
                        )}
                      >
                        <Icon className="size-4" />
                      </span>
                      <span className="text-[13px] leading-[20px] text-muted-foreground group-hover:text-foreground">
                        {prompt}
                      </span>
                    </motion.button>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="mx-auto flex w-full max-w-[760px] flex-col gap-5 px-6 py-6">
              <AnimatePresence initial={false}>
                {messages.map((message) => {
                  // Check if this is a clarification message from tool
                  if (
                    message.role === "assistant" &&
                    message.content.includes("❓") ||
                    message.content.includes("🤔") ||
                    message.content.includes("🔀") ||
                    message.content.includes("⚠️") ||
                    message.content.includes("💡")
                  ) {
                    // Try to parse as clarification
                    try {
                      const parsed = parseClarificationContent(message.content);
                      // Only render as clarification if it has the expected format
                      if (parsed.question && parsed.clarificationType) {
                        return (
                          <ClarificationCard
                            key={message.id}
                            question={parsed.question}
                            context={parsed.context}
                            options={parsed.options}
                            clarificationType={parsed.clarificationType}
                            onRespond={(response) => {
                              // Use message.id as tool_call_id fallback
                              handleClarificationRespond(response, message.id);
                            }}
                          />
                        );
                      }
                    } catch {
                      // Fall through to normal rendering
                    }
                  }
                  
                  return (
                    <motion.div
                      key={message.id}
                      initial={{ opacity: 0, y: 12 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
                    >
                      <MessageBubble
                        key={message.id}
                        message={message}
                        isMessageStreaming={
                          message.isStreaming || message.isReasoningStreaming
                        }
                      />
                    </motion.div>
                  );
                })}
              </AnimatePresence>
              
              {/* Render ClarificationCard if there's a pending clarification */}
              {pendingClarification && (
                <motion.div
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
                  className="mt-4"
                >
                  {(() => {
                    const parsed = parseClarificationContent(pendingClarification.content);
                    return (
                      <ClarificationCard
                        question={parsed.question}
                        context={parsed.context}
                        options={parsed.options}
                        clarificationType={parsed.clarificationType}
                        onRespond={(response) => {
                          handleClarificationRespond(response, pendingClarification.id);
                          setPendingClarification(null); // Clear after response
                        }}
                      />
                    );
                  })()}
                </motion.div>
              )}
              
              {/* Render SubtaskCards for active tasks */}
              {Object.values(tasks).length > 0 && (
                <div className="flex flex-col gap-3 mt-4">
                  <div className="text-muted-foreground text-sm">
                    正在执行 {Object.values(tasks).length} 个子任务...
                  </div>
                  {Object.values(tasks).map((task) => (
                    <SubtaskCard
                      key={task.id}
                      taskId={task.id}
                      isLoading={isLoading}
                    />
                  ))}
                </div>
              )}
              
              {isLoading &&
                !messages.some(
                  (m) => m.content.trim().length > 0 && m.role === "assistant",
                ) && (
                  <motion.div
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.2 }}
                    className="flex justify-start"
                  >
                    <div className="flex items-center gap-2 rounded-lg border border-border bg-secondary px-4 py-2">
                      <StreamingDots />
                      <span className="text-[13px] text-muted-foreground">
                        正在生成回复
                      </span>
                    </div>
                  </motion.div>
                )}
            </div>
          )}
        </div>

        <AnimatePresence>
          {showScrollToLatest && !isConversationLoading && !isEmpty ? (
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 12 }}
              transition={{ duration: 0.18, ease: "easeOut" }}
              className="pointer-events-none absolute inset-x-0 bottom-3 z-10 flex justify-center px-6"
            >
              <Button
                type="button"
                variant="outline"
                size="icon"
                onClick={() => scrollToLatest("smooth")}
                aria-label="回到最新"
                title="回到最新"
                className="pointer-events-auto size-10 rounded-full border-border bg-card shadow-none hover:bg-card"
              >
                <ArrowDown className="size-3.5" />
              </Button>
            </motion.div>
          ) : null}
        </AnimatePresence>
      </div>

      {/* Pinned bottom: status + composer as unified container */}
      <div className="sticky bottom-0 z-20">
        <div className="relative border-t border-border/70 bg-background">
          <div className="mx-auto w-full max-w-[760px] px-6 pb-5 pt-2.5">
            <div className="rounded-[14px] border border-border bg-card transition-[border-color,box-shadow] focus-within:border-[#bec8d0] focus-within:ring-[3px] focus-within:ring-[#e7ecef]/80">
              {(runtime.phase !== "idle" || error) && (
                <div
                  className="border-b border-border bg-secondary px-5 py-2.5"
                  aria-live="polite"
                >
                  <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                    <p className="text-[13px] text-muted-foreground">
                      {error || runtime.label}
                    </p>
                    <Badge
                      variant="outline"
                      className={cn("text-[11px]", statusTone(runtime.phase))}
                    >
                      {statusLabel(runtime.phase)}
                    </Badge>
                  </div>
                </div>
              )}

              <div>
                <Textarea
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      void handleSubmit();
                    }
                  }}
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
                <div className="flex flex-col gap-2 border-t border-border bg-secondary/70 px-4 py-2.5 sm:flex-row sm:items-center sm:justify-between">
                  <div className="flex flex-wrap items-center gap-2">
                    <ModePicker
                      selected={selectedMode}
                      onSelect={setSelectedMode}
                    />
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      disabled
                      className="size-10 rounded-md border border-transparent text-muted-foreground hover:border-border hover:bg-card"
                      title="上传附件"
                    >
                      <Paperclip className="size-4" />
                    </Button>
                    {lastAssistantMessage && (
                      <Button
                        variant="ghost"
                        size="icon-sm"
                        className="size-10 rounded-md border border-transparent text-muted-foreground hover:border-border hover:bg-card"
                        onClick={() =>
                          navigator.clipboard.writeText(
                            lastAssistantMessage.content,
                          )
                        }
                        title="复制回复"
                      >
                        <Copy className="size-4" />
                      </Button>
                    )}
                  </div>
                  <div className="flex flex-wrap items-center justify-between gap-2 sm:justify-end">
                    <ModelPicker
                      models={modelOptions}
                      selected={selectedModel}
                      onSelect={setSelectedModel}
                      isLoading={isModelsLoading}
                      loadError={modelLoadError}
                      onRetry={() => {
                        void fetchModels();
                      }}
                    />
                    <Button
                      onClick={() => void handleSubmit()}
                      disabled={!input.trim() || isComposerDisabled}
                      size="icon-sm"
                      className="size-10 rounded-md shadow-none"
                    >
                      {isLoading ? (
                        <Loader2 className="size-4 animate-spin" />
                      ) : (
                        <ArrowUp className="size-4" />
                      )}
                    </Button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
    </ChatLayout>
    </ArtifactsProvider>
  );
}

// ============================================================================
// V0Chat - Wrapper with SubtasksProvider
// ============================================================================

export function V0Chat(props: V0ChatProps) {
  return (
    <SubtasksProvider>
      <V0ChatInner {...props} />
    </SubtasksProvider>
  );
}

// ============================================================================
// ChatLayout - Two-panel layout with Artifacts (Simplified from DeerFlow)
// ============================================================================

interface ChatLayoutProps {
  children: React.ReactNode;
  conversationId?: string;
  artifacts: string[];
  selectedArtifact: string | null;
  onSelectArtifact: (path: string | null) => void;
  artifactsOpen: boolean;
  setArtifactsOpen: (open: boolean) => void;
}

function ChatLayout({
  children,
  conversationId,
  artifacts,
  selectedArtifact,
  onSelectArtifact,
  artifactsOpen,
  setArtifactsOpen,
}: ChatLayoutProps) {
  return (
    <div className="flex h-full w-full">
      {/* Left Panel - Chat */}
      <div className={cn(
        "relative flex flex-col h-full transition-all duration-300",
        artifactsOpen ? "w-[60%]" : "w-full"
      )}>
        {children}
      </div>

      {/* Resize Handle - Only show when artifacts panel is open */}
      {artifactsOpen && (
        <div className="w-px bg-border hover:bg-border/80 cursor-col-resize" />
      )}

      {/* Right Panel - Artifacts */}
      {artifactsOpen && (
        <div className="w-[40%] min-w-[300px] max-w-[600px] bg-background border-l flex flex-col h-full">
          {/* Artifacts Header */}
          <div className="flex items-center justify-between border-b px-4 py-3">
            <h3 className="font-medium text-sm">Artifacts</h3>
            <div className="flex items-center gap-2">
              {artifacts.length > 0 && (
                <span className="text-muted-foreground text-xs">
                  {artifacts.length} 个文件
                </span>
              )}
              <Button
                variant="ghost"
                size="icon-sm"
                onClick={() => setArtifactsOpen(false)}
              >
                <XIcon className="size-4" />
              </Button>
            </div>
          </div>

          {/* Artifacts Content */}
          <div className="flex-1 overflow-hidden">
            {artifacts.length === 0 ? (
              <div className="flex h-full flex-col items-center justify-center p-8 text-center">
                <FilesIcon className="size-12 text-muted-foreground/50 mb-4" />
                <h4 className="text-sm font-medium mb-2">没有 Artifacts</h4>
                <p className="text-muted-foreground text-xs max-w-[200px]">
                  当 AI 生成文件时，它们将显示在这里
                </p>
              </div>
            ) : selectedArtifact ? (
              <div className="h-full flex flex-col">
                <div className="flex items-center justify-between border-b px-4 py-2 bg-muted/50">
                  <span className="text-sm font-medium truncate max-w-[200px]">
                    {selectedArtifact.split('/').pop()}
                  </span>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => onSelectArtifact(null)}
                  >
                    返回列表
                  </Button>
                </div>
                <div className="flex-1 overflow-auto p-4">
                  <iframe
                    src={`/api/conversations/${conversationId}/artifacts${selectedArtifact}`}
                    className="w-full h-full border rounded-lg"
                    title={selectedArtifact}
                  />
                </div>
              </div>
            ) : (
              <div className="p-4">
                <ArtifactFileListSimple
                  files={artifacts}
                  onSelect={onSelectArtifact}
                />
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ============================================================================
// Simplified Artifact File List for ChatLayout
// ============================================================================

interface ArtifactFileListSimpleProps {
  files: string[];
  onSelect: (path: string) => void;
}

function ArtifactFileListSimple({ files, onSelect }: ArtifactFileListSimpleProps) {
  return (
    <div className="flex flex-col gap-2">
      {files.map((file) => (
        <button
          key={file}
          onClick={() => onSelect(file)}
          className="flex items-center gap-3 rounded-lg border p-3 text-left hover:bg-muted transition-colors"
        >
          <FilesIcon className="size-5 text-muted-foreground" />
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium truncate">
              {file.split('/').pop()}
            </p>
            <p className="text-xs text-muted-foreground truncate">
              {file}
            </p>
          </div>
        </button>
      ))}
    </div>
  );
}
