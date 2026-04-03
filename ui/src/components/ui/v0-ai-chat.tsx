"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Streamdown } from "streamdown";
import "streamdown/styles.css";
import remarkGfm from "remark-gfm";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@radix-ui/react-collapsible";
import { useControllableState } from "@radix-ui/react-use-controllable-state";
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
import { Shimmer } from "@/components/ui/shimmer";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";

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

interface RuntimeTask {
  id: string;
  title: string;
  status: "running" | "completed" | "failed";
  detail?: string;
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
  tasks: RuntimeTask[];
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
      type: "team_task";
      task: Partial<RuntimeTask> & {
        id: string;
      };
    }
  | {
      type: "team_activity";
      activity: {
        id: string;
        label: string;
        status: RuntimeActivity["status"];
        detail?: string | null;
      };
    }
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
    accentClassName:
      "from-[#cfe5ff] via-[#e8f3ff] to-white text-[#184a88] border-[#b9d3f5]",
    icon: Zap,
  },
  {
    id: "thinking",
    label: "Thinking",
    description: "保留推理过程，单轮深入分析",
    accentClassName:
      "from-[#ece4ff] via-[#f6f0ff] to-white text-[#5f38a6] border-[#d9c8ff]",
    icon: Lightbulb,
  },
  {
    id: "pro",
    label: "Pro",
    description: "先规划再执行",
    accentClassName:
      "from-[#dff5eb] via-[#eefbf4] to-white text-[#0d6b4b] border-[#bfe7d3]",
    icon: GraduationCap,
  },
  {
    id: "ultra",
    label: "Ultra",
    description: "启用完整协作流程",
    accentClassName:
      "from-[#fff0bd] via-[#fff8df] to-white text-[#8a5a00] border-[#ecd48a]",
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
    tasks: [],
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

function upsertTask(
  tasks: RuntimeTask[],
  patch: Partial<RuntimeTask> & { id: string },
) {
  const index = tasks.findIndex((task) => task.id === patch.id);
  if (index === -1) {
    return [
      ...tasks,
      {
        id: patch.id,
        title: patch.title ?? "新的处理步骤",
        status: patch.status ?? "running",
        detail: patch.detail,
      },
    ];
  }

  const next = [...tasks];
  next[index] = {
    ...next[index],
    ...patch,
    title: patch.title ?? next[index].title,
    status: patch.status ?? next[index].status,
  };
  return next;
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
        className={cn(
          "group flex h-8 items-center gap-1.5 rounded-full border bg-gradient-to-r px-2.5 text-left shadow-[0_10px_24px_-20px_rgba(15,23,42,0.4)] transition-all hover:border-border hover:shadow-[0_12px_24px_-20px_rgba(15,23,42,0.28)]",
          current.accentClassName,
        )}
      >
        <span className="flex size-5 items-center justify-center rounded-full bg-white/80 shadow-sm">
          <CurrentIcon className="size-3" />
        </span>
        <span className="min-w-0">
          <span className="block text-[11px] leading-4 font-semibold tracking-[0.02em]">
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
              className="absolute bottom-full left-0 z-50 mb-2.5 w-[286px] rounded-[20px] border border-border/70 bg-[linear-gradient(180deg,rgba(255,255,255,0.98),rgba(247,248,250,0.96))] p-2.5 shadow-[0_22px_54px_-30px_rgba(15,23,42,0.34)] backdrop-blur"
            >
              <div className="mb-1.5 px-1">
                <p className="text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
                  Mode
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
                        "flex w-full items-start gap-2.5 rounded-[16px] border bg-white/70 px-3 py-2.5 text-left transition-all",
                        isSelected
                          ? cn(
                              "shadow-[0_14px_30px_-22px_rgba(15,23,42,0.45)]",
                              mode.accentClassName,
                            )
                          : "border-border/70 text-foreground hover:border-border hover:bg-white",
                      )}
                    >
                      <span
                        className={cn(
                          "mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-full border bg-white/80 shadow-sm",
                          isSelected ? "border-white/70" : "border-border/70",
                        )}
                      >
                        <Icon className="size-3.5" />
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="flex items-center gap-1.5">
                          <span className="text-[12px] font-semibold">
                            {mode.label}
                          </span>
                          {isSelected ? (
                            <span className="rounded-full bg-white/80 px-1.5 py-0.5 text-[9px] font-medium uppercase tracking-[0.16em]">
                              Active
                            </span>
                          ) : null}
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
        className="flex h-8 items-center gap-1.5 rounded-md px-2 text-[12px] text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
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
              className="absolute bottom-full left-0 z-50 mb-2 w-[180px] overflow-hidden rounded-lg border border-border bg-popover p-1 shadow-md"
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
                    "flex w-full items-center gap-2 rounded-md px-2.5 py-2 text-[13px] transition-colors",
                    model.name === selected
                      ? "bg-accent text-foreground font-medium"
                      : "text-muted-foreground hover:bg-accent hover:text-foreground",
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
        isUser ? "justify-end" : "justify-start",
      )}
    >
      <div
        className={cn(
          "relative max-w-[88%] border",
          isUser
            ? "rounded-[22px] border-[#c9ddff] bg-[#dcebff] px-[18px] py-3 text-[#23395b] shadow-[0_10px_24px_-22px_rgba(44,98,170,0.55)]"
            : "rounded-[26px] border-border/70 bg-[linear-gradient(180deg,rgba(255,255,255,0.98),rgba(248,250,252,0.96))] px-5 py-4 shadow-[0_16px_36px_-28px_rgba(15,23,42,0.3)] md:px-6 md:py-5",
        )}
      >
        {message.content.trim().length > 0 ? (
          <div className="absolute -right-1 -top-1 opacity-0 transition-opacity md:group-hover:opacity-100 md:group-focus-within:opacity-100">
            <Button
              type="button"
              variant="ghost"
              size="icon-xs"
              onClick={() => {
                void handleCopy();
              }}
              className="h-6 w-6 rounded-full border border-border/70 bg-white/95 text-muted-foreground shadow-sm backdrop-blur hover:bg-white hover:text-foreground"
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
          <ReasoningPanel
            thinking={message.thinking}
            isStreaming={message.isReasoningStreaming}
          />
        ) : null}

        {message.content ? (
          isUser ? (
            <div className="whitespace-pre-wrap font-[var(--font-body)] text-[14px] leading-[22px]">
              {message.content}
            </div>
          ) : (
            <div className="prose prose-sm max-w-none pl-0.5 pr-1 font-[var(--font-body)] text-[14px] leading-[24px] text-foreground prose-headings:mt-0 prose-headings:mb-3 prose-headings:font-sans prose-p:my-0 prose-p:font-body prose-p:leading-[24px] prose-pre:my-4 prose-pre:mx-0 prose-code:font-mono prose-li:font-body prose-ul:my-3 prose-ul:pl-5 prose-ol:my-3 prose-ol:pl-5 prose-li:my-1">
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

function ReasoningPanel({
  thinking,
  isStreaming = false,
}: {
  thinking: string;
  isStreaming?: boolean;
}) {
  const [isOpen, setIsOpen] = useControllableState({
    defaultProp: true,
  });
  const [hasAutoClosed, setHasAutoClosed] = useState(false);
  const [durationSeconds, setDurationSeconds] = useState<number | undefined>(
    undefined,
  );
  const [startTime, setStartTime] = useState<number | null>(null);

  // Track duration when streaming starts/ends
  useEffect(() => {
    if (isStreaming) {
      if (startTime === null) {
        setStartTime(Date.now());
      }
    } else if (startTime !== null) {
      setDurationSeconds(
        Math.max(1, Math.ceil((Date.now() - startTime) / 1000)),
      );
      setStartTime(null);
    }
  }, [isStreaming, startTime]);

  // Auto-close after streaming ends (once only)
  useEffect(() => {
    if (
      !isStreaming &&
      isOpen &&
      !hasAutoClosed &&
      durationSeconds !== undefined
    ) {
      const timer = window.setTimeout(() => {
        setIsOpen(false);
        setHasAutoClosed(true);
      }, 1000);
      return () => window.clearTimeout(timer);
    }
  }, [isStreaming, isOpen, hasAutoClosed, durationSeconds, setIsOpen]);

  const triggerContent =
    isStreaming || durationSeconds === undefined ? (
      <Shimmer duration={1}>{"模型正在思考..."}</Shimmer>
    ) : (
      <span>{`思考完成，用时 ${durationSeconds} 秒`}</span>
    );

  return (
    <Collapsible
      open={isOpen}
      onOpenChange={setIsOpen}
      className="mb-3 rounded-md border border-border bg-secondary/90"
    >
      <CollapsibleTrigger className="flex w-full items-center gap-2 px-3 py-2 text-left text-[12px] leading-[18px] text-muted-foreground transition-colors hover:text-foreground">
        <Brain className="size-3.5 shrink-0" />
        <span className="flex-1">{triggerContent}</span>
        <ChevronDown
          className={cn(
            "size-3.5 shrink-0 transition-transform duration-200",
            isOpen && "rotate-180",
          )}
        />
      </CollapsibleTrigger>

      <CollapsibleContent className="overflow-hidden data-[state=closed]:animate-accordion-up data-[state=open]:animate-accordion-down">
        <div className="border-t border-border/70 px-3 py-2 text-[12px] leading-[18px] text-muted-foreground">
          <Streamdown
            mode={isStreaming ? "streaming" : "static"}
            remarkPlugins={staticRemarkPlugins}
          >
            {thinking}
          </Streamdown>
        </div>
      </CollapsibleContent>
    </Collapsible>
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
    <div className="mx-auto flex w-full max-w-[760px] flex-col gap-8 px-6 py-6">
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
        <div className="w-full max-w-[520px] rounded-2xl border border-border/70 bg-card px-4 py-4">
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

export function V0Chat({
  conversationId,
  draftResetToken,
  onConversationCreated,
  onConversationsChange,
}: V0ChatProps) {
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

  const resetDraftState = useCallback(() => {
    setCurrentConversationId(undefined);
    setMessages([]);
    setRuntime(createEmptyRuntime());
    setIsConversationLoading(false);
    setError(null);
    setInput("");
    setSelectedMode(DEFAULT_MODE);
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
              isReasoningStreaming: next[index].isReasoningStreaming,
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
              isReasoningStreaming:
                next[activeAssistantIndex].isReasoningStreaming,
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
            next[activeAssistantIndex] = {
              ...next[activeAssistantIndex],
              ...event.message,
              isStreaming: false,
              isReasoningStreaming: false,
            };
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

      case "team_task":
        setRuntime((previous) => ({
          ...previous,
          tasks: upsertTask(previous.tasks, {
            id: event.task.id,
            title: event.task.title,
            status: event.task.status,
            detail: event.task.detail,
          }),
        }));
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
  }, []);

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
  const currentModeOption =
    MODE_OPTIONS.find((mode) => mode.id === selectedMode) ?? MODE_OPTIONS[0];

  return (
    <div className="relative flex min-h-0 flex-1 flex-col overflow-hidden bg-background">
      {/* Subtle background atmosphere */}
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_80%_60%_at_50%_-10%,hsla(214,67%,77%,0.08),transparent)]" />
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_400px_at_20%_80%,hsla(259,45%,89%,0.05),transparent)]" />

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
            <div className="flex flex-1 flex-col px-6 pt-16">
              <div className="mx-auto w-full max-w-[560px]">
                <motion.div
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
                  className="mb-8"
                >
                  <div className="inline-flex items-center gap-2 rounded-full border border-border/60 bg-card px-3 py-1.5 text-[12px] text-muted-foreground">
                    <Sparkles className="size-3.5 text-primary" />
                    SwarmMind v0.9
                  </div>
                  <h2 className="mt-4 text-3xl font-semibold tracking-tight text-foreground">
                    临时会话
                  </h2>
                  <p className="mt-2 max-w-[420px] text-[15px] leading-relaxed text-muted-foreground">
                    快速探索、生成和试跑想法。首次发送成功后才会创建正式会话。
                  </p>
                </motion.div>

                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 0.15, duration: 0.2 }}
                  className="mb-3 flex items-center gap-2"
                >
                  <p className="text-[12px] font-medium uppercase tracking-wider text-muted-foreground">
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
                      className="group flex items-start gap-3 rounded-xl border border-border/70 bg-card/60 p-4 text-left transition-all hover:border-border hover:bg-card hover:shadow-[0_4px_16px_-8px_rgba(0,0,0,0.08)]"
                    >
                      <span
                        className={cn(
                          "mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-lg transition-colors",
                          i === 0
                            ? "bg-[#dcebff] text-[#184a88]"
                            : i === 1
                              ? "bg-[#fff0bd] text-[#8a5a00]"
                              : i === 2
                                ? "bg-[#eee6ff] text-[#5f38a6]"
                                : "bg-[#dff5eb] text-[#0d6b4b]",
                        )}
                      >
                        <Icon className="size-4" />
                      </span>
                      <span className="text-[13px] leading-snug text-muted-foreground group-hover:text-foreground">
                        {prompt}
                      </span>
                    </motion.button>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="mx-auto flex w-full max-w-[760px] flex-col gap-4 px-6 py-6">
              <AnimatePresence initial={false}>
                {messages.map((message) => (
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
                ))}
              </AnimatePresence>
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
                    <div className="flex items-center gap-2 rounded-full border border-border bg-card px-4 py-2.5 shadow-sm">
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
              className="pointer-events-none absolute bottom-[140px] left-1/2 z-10 -translate-x-1/2"
            >
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => scrollToLatest("smooth")}
                className="pointer-events-auto rounded-full border-border bg-background/95 shadow-[0_10px_30px_-18px_rgba(15,23,42,0.45)] backdrop-blur"
              >
                <ArrowDown className="size-3.5" />
                回到最新
              </Button>
            </motion.div>
          ) : null}
        </AnimatePresence>
      </div>

      {/* Pinned bottom: status + composer as unified container */}
      <div className="sticky bottom-0 z-20 border-t border-border/60 bg-background/94 shadow-[0_-18px_38px_-30px_rgba(15,23,42,0.35)] backdrop-blur supports-[backdrop-filter]:bg-background/82">
        <div className="mx-auto w-full max-w-[760px] px-6 pb-5 pt-3">
          <div className="rounded-2xl border border-border bg-card shadow-[0_4px_24px_-12px_rgba(0,0,0,0.08)] transition-[border-color,box-shadow] focus-within:border-[#a8c8ff] focus-within:shadow-[0_4px_24px_-12px_rgba(100,160,255,0.18)] focus-within:ring-[3px] focus-within:ring-[#a8c8ff]/30">
            {/* Mode indicator accent bar */}
            <div className="overflow-hidden rounded-t-2xl">
              <div
                className={cn(
                  "h-[2px] bg-gradient-to-r from-transparent via-60% to-transparent transition-all duration-500",
                  currentModeOption.id === "flash"
                    ? "via-[#a8c8ff]"
                    : currentModeOption.id === "thinking"
                      ? "via-[#c8a8ff]"
                      : currentModeOption.id === "pro"
                        ? "via-[#8ad4a8]"
                        : "via-[#ffcf5a]",
                )}
              />
            </div>
            {(runtime.phase !== "idle" || error) && (
              <div
                className="border-b border-border/70 bg-secondary/50 px-5 py-2.5"
                aria-live="polite"
              >
                <div className="flex items-center justify-between">
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
                className="min-h-[100px] resize-none border-none bg-transparent px-5 py-4 text-[15px] focus-visible:ring-0"
                disabled={isComposerDisabled}
              />
              <div className="flex items-center justify-between border-t border-border px-4 py-2.5">
                <div className="flex items-center gap-1">
                  <ModePicker
                    selected={selectedMode}
                    onSelect={setSelectedMode}
                  />
                  <Button
                    variant="ghost"
                    size="icon-xs"
                    disabled
                    className="text-muted-foreground"
                    title="上传附件"
                  >
                    <Paperclip className="size-4" />
                  </Button>
                  {lastAssistantMessage && (
                    <Button
                      variant="ghost"
                      size="icon-xs"
                      className="text-muted-foreground"
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
                <div className="flex items-center gap-1.5">
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
                    className="rounded-lg"
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
  );
}
