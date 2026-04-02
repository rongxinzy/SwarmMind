"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import {
  AnimatePresence,
  motion,
} from "framer-motion";
import {
  ArrowUp,
  Brain,
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
  thinkingByMessageId: Record<string, string>;
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
};

type ConversationMode = "flash" | "thinking" | "pro" | "ultra";

const QUICK_PROMPTS = [
  "帮我整理本周项目进展，输出 3 条重点结论。",
  "生成一版 CRM MVP 范围说明，控制在一页内。",
  "把下面的会议讨论改写成正式纪要。",
  "总结当前续费风险，并给出 3 条行动建议。",
];

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
    accentClassName: "from-[#cfe5ff] via-[#e8f3ff] to-white text-[#184a88] border-[#b9d3f5]",
    icon: Zap,
  },
  {
    id: "thinking",
    label: "Thinking",
    description: "保留推理过程，单轮深入分析",
    accentClassName: "from-[#ece4ff] via-[#f6f0ff] to-white text-[#5f38a6] border-[#d9c8ff]",
    icon: Lightbulb,
  },
  {
    id: "pro",
    label: "Pro",
    description: "默认模式，先规划再执行",
    accentClassName: "from-[#dff5eb] via-[#eefbf4] to-white text-[#0d6b4b] border-[#bfe7d3]",
    icon: GraduationCap,
  },
  {
    id: "ultra",
    label: "Ultra",
    description: "启用完整协作流程",
    accentClassName: "from-[#fff0bd] via-[#fff8df] to-white text-[#8a5a00] border-[#ecd48a]",
    icon: Rocket,
  },
];

const DEFAULT_MODE: ConversationMode = "pro";
const DEFAULT_MODEL = "qwen3.5-plus";

function generateId() {
  return Math.random().toString(36).slice(2, 10);
}

function createEmptyRuntime(): RuntimeState {
  return {
    phase: "idle",
    label: "等待新的输入",
    tasks: [],
    activities: [],
    thinkingByMessageId: {},
  };
}

function sortConversations(items: ConversationRecord[]) {
  return [...items].sort((a, b) => {
    const left = new Date(a.updated_at).getTime();
    const right = new Date(b.updated_at).getTime();
    return right - left;
  });
}

function upsertTask(tasks: RuntimeTask[], patch: Partial<RuntimeTask> & { id: string }) {
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
  patch: Partial<RuntimeActivity> & { id: string; label: string; status: RuntimeActivity["status"] },
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
  if (phase === "routing" || phase === "running" || phase === "accepted") return "status-pill-running";
  return "status-pill-draft";
}

function statusLabel(phase: RuntimeState["phase"]) {
  if (phase === "accepted") return "已提交";
  if (phase === "routing" || phase === "running") return "生成中";
  if (phase === "completed") return "已完成";
  if (phase === "error") return "失败";
  return "待开始";
}

const MODEL_OPTIONS = [
  { id: "qwen3.5-plus", label: "Qwen 3.5 Plus" },
  { id: "qwen3.5-turbo", label: "Qwen 3.5 Turbo" },
  { id: "deepseek-r1", label: "DeepSeek R1" },
  { id: "claude-sonnet-4-6", label: "Claude Sonnet 4.6" },
];

function ModePicker({
  selected,
  onSelect,
}: {
  selected: ConversationMode;
  onSelect: (id: ConversationMode) => void;
}) {
  const [open, setOpen] = useState(false);
  const current = MODE_OPTIONS.find((mode) => mode.id === selected) ?? MODE_OPTIONS[0];
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
            <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
            <motion.div
              initial={{ opacity: 0, y: 8, scale: 0.97 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 8, scale: 0.97 }}
              transition={{ type: "spring", stiffness: 360, damping: 28, mass: 0.9 }}
              className="absolute bottom-full left-0 z-50 mb-3 w-[320px] rounded-[22px] border border-border/70 bg-[linear-gradient(180deg,rgba(255,255,255,0.98),rgba(247,248,250,0.96))] p-3 shadow-[0_24px_60px_-30px_rgba(15,23,42,0.35)] backdrop-blur"
            >
              <div className="mb-2 px-1">
                <p className="text-[11px] uppercase tracking-[0.22em] text-muted-foreground">Mode</p>
                <p className="text-[13px] text-foreground">选择这轮临时会话的执行方式</p>
              </div>
              <div className="space-y-2">
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
                        "flex w-full items-start gap-3 rounded-[18px] border bg-white/70 px-3.5 py-3 text-left transition-all",
                        isSelected
                          ? cn("shadow-[0_14px_30px_-22px_rgba(15,23,42,0.45)]", mode.accentClassName)
                          : "border-border/70 text-foreground hover:border-border hover:bg-white",
                      )}
                    >
                      <span
                        className={cn(
                          "mt-0.5 flex size-9 shrink-0 items-center justify-center rounded-full border bg-white/80 shadow-sm",
                          isSelected ? "border-white/70" : "border-border/70",
                        )}
                      >
                        <Icon className="size-4" />
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="flex items-center gap-2">
                          <span className="text-[13px] font-semibold">{mode.label}</span>
                          {isSelected ? (
                            <span className="rounded-full bg-white/80 px-2 py-0.5 text-[10px] font-medium uppercase tracking-[0.18em]">
                              Active
                            </span>
                          ) : null}
                        </span>
                        <span className="mt-1 block text-[12px] leading-5 opacity-80">
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
  selected,
  onSelect,
}: {
  selected: string;
  onSelect: (id: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const current = MODEL_OPTIONS.find((m) => m.id === selected) ?? MODEL_OPTIONS[0];

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        className="flex h-8 items-center gap-1.5 rounded-md px-2 text-[12px] text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
      >
        <Sparkles className="size-3.5" />
        <span className="max-w-[100px] truncate">{current.label}</span>
      </button>

      <AnimatePresence>
        {open && (
          <>
            <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
            <motion.div
              initial={{ opacity: 0, y: 4, scale: 0.96 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 4, scale: 0.96 }}
              transition={{ type: "spring", stiffness: 500, damping: 30, mass: 0.8 }}
              className="absolute bottom-full left-0 z-50 mb-2 w-[180px] overflow-hidden rounded-lg border border-border bg-popover p-1 shadow-md"
            >
              {MODEL_OPTIONS.map((model) => (
                <button
                  key={model.id}
                  type="button"
                  onClick={() => {
                    onSelect(model.id);
                    setOpen(false);
                  }}
                  className={cn(
                    "flex w-full items-center gap-2 rounded-md px-2.5 py-2 text-[13px] transition-colors",
                    model.id === selected
                      ? "bg-accent text-foreground font-medium"
                      : "text-muted-foreground hover:bg-accent hover:text-foreground",
                  )}
                >
                  <Sparkles className="size-3.5 shrink-0" />
                  <span className="truncate">{model.label}</span>
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
  thinking,
}: {
  message: ChatMessage;
  thinking?: string;
}) {
  const isUser = message.role === "user";

  return (
    <div className={cn("flex w-full", isUser ? "justify-end" : "justify-start")}>
      <div
        className={cn(
          "max-w-[88%] rounded-lg border px-4 py-3",
          isUser ? "border-[#c9ddff] bg-[#dcebff] text-[#23395b]" : "border-border bg-card text-foreground",
        )}
      >
        {!isUser && thinking ? (
          <details className="mb-3 rounded-md border border-border bg-secondary px-3 py-2">
            <summary className="flex cursor-pointer list-none items-center gap-2 text-[12px] leading-[18px] text-muted-foreground">
              <Brain className="size-3.5" />
              模型过程
            </summary>
            <div className="mt-2 whitespace-pre-wrap text-[12px] leading-[18px] text-muted-foreground">
              {thinking}
            </div>
          </details>
        ) : null}

        {message.content ? (
          isUser ? (
            <div className="whitespace-pre-wrap text-[14px] leading-[22px]">{message.content}</div>
          ) : (
            <div className="prose prose-sm max-w-none text-[14px] leading-[22px] text-foreground">
              <ReactMarkdown>{message.content}</ReactMarkdown>
            </div>
          )
        ) : (
          <div className="flex items-center gap-2 text-[14px] leading-[22px] text-muted-foreground">
            <Loader2 className="size-4 animate-spin" />
            正在整理回复
          </div>
        )}
      </div>
    </div>
  );
}

export function V0Chat({ conversationId, draftResetToken, onConversationCreated, onConversationsChange }: V0ChatProps) {
  const [conversations, setConversations] = useState<ConversationRecord[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [runtime, setRuntime] = useState<RuntimeState>(createEmptyRuntime());
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [selectedMode, setSelectedMode] = useState<ConversationMode>(DEFAULT_MODE);
  const [selectedModel, setSelectedModel] = useState(DEFAULT_MODEL);
  const [error, setError] = useState<string | null>(null);
  const [currentConversationId, setCurrentConversationId] = useState<string | undefined>(conversationId);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const resetDraftState = useCallback(() => {
    setCurrentConversationId(undefined);
    setMessages([]);
    setRuntime(createEmptyRuntime());
    setError(null);
    setInput("");
    setSelectedMode(DEFAULT_MODE);
    setSelectedModel(DEFAULT_MODEL);
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
    try {
      const response = await fetch(`/conversations/${nextConversationId}/messages`);
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
      setRuntime(createEmptyRuntime());
      setError(null);
    } catch (requestError) {
      console.error("Failed to load messages:", requestError);
      setError(requestError instanceof Error ? requestError.message : "加载会话失败");
    }
  }, []);

  useEffect(() => {
    void fetchConversations();
  }, [fetchConversations]);

  useEffect(() => {
    onConversationsChange?.(conversations);
  }, [conversations, onConversationsChange]);

  useEffect(() => {
    if (conversationId) {
      setCurrentConversationId(conversationId);
      void loadMessages(conversationId);
      return;
    }

    resetDraftState();
  }, [conversationId, loadMessages, resetDraftState, draftResetToken]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, runtime]);

  const lastAssistantMessage = useMemo(
    () => [...messages].reverse().find((message) => message.role === "assistant" && message.content.trim().length > 0),
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
        sortConversations([record, ...previous.filter((item) => item.id !== record.id)]),
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
        }
        return;

      case "user_message":
        setMessages((previous) => {
          const pendingIndex = [...previous].reverse().findIndex(
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
        setRuntime((previous) => ({
          ...previous,
          thinkingByMessageId: {
            ...previous.thinkingByMessageId,
            [event.message_id]: previous.thinkingByMessageId[event.message_id]
              ? `${previous.thinkingByMessageId[event.message_id]}\n${event.content}`
              : event.content,
          },
        }));
        return;

      case "assistant_message":
        setMessages((previous) => {
          const index = previous.findIndex((message) => message.id === event.message_id);
          if (index !== -1) {
            const next = [...previous];
            next[index] = {
              ...next[index],
              content: event.content,
              isStreaming: true,
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
            },
          ];
        });
        return;

      case "assistant_final":
        setMessages((previous) => {
          const exactIndex = previous.findIndex((message) => message.id === event.message.id);
          if (exactIndex !== -1) {
            const next = [...previous];
            next[exactIndex] = {
              ...next[exactIndex],
              ...event.message,
              isStreaming: false,
            };
            return next;
          }

          const streamingIndex = [...previous].reverse().findIndex(
            (message) => message.role === "assistant" && message.isStreaming,
          );
          if (streamingIndex !== -1) {
            const actualIndex = previous.length - 1 - streamingIndex;
            const next = [...previous];
            next[actualIndex] = {
              ...next[actualIndex],
              ...event.message,
              isStreaming: false,
            };
            return next;
          }

          return [
            ...previous,
            {
              ...event.message,
              isStreaming: false,
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
            ...previous.filter((conversation) => conversation.id !== event.conversation.id),
          ]),
        );
        return;

      case "done":
        setIsLoading(false);
    }
  }, []);

  const streamConversation = useCallback(
    async (nextConversationId: string, text: string, mode: ConversationMode, modelName: string) => {
      const response = await fetch(`/conversations/${nextConversationId}/messages/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          content: text,
          mode,
          model_name: modelName,
        }),
      });

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

      if (!prompt) setInput("");

      setError(null);
      setIsLoading(true);
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
        const nextConversationId = currentConversationId ?? (await createConversation(text.slice(0, 60)));
        await streamConversation(nextConversationId, text, selectedMode, selectedModel);
        await fetchConversations();
      } catch (requestError) {
        setIsLoading(false);
        const message =
          requestError instanceof Error ? requestError.message : "发送消息时发生未知错误";
        setError(message);
        setRuntime((previous) => ({
          ...previous,
          phase: "error",
          label: `会话执行失败：${message}`,
        }));
      }
    },
    [createConversation, currentConversationId, fetchConversations, input, isLoading, selectedMode, selectedModel, streamConversation],
  );

  const isEmpty = messages.length === 0 && !isLoading;
  const currentModeOption = MODE_OPTIONS.find((mode) => mode.id === selectedMode) ?? MODE_OPTIONS[0];

  return (
    <div className="flex h-[calc(100vh-65px)] flex-col bg-background md:h-screen">
      {/* Scrollable area: messages OR empty-state */}
      <div className="flex flex-1 flex-col overflow-y-auto">
        {isEmpty ? (
          <div className="flex flex-1 flex-col items-center justify-center px-6">
            <div className="mx-auto flex size-14 items-center justify-center rounded-full bg-primary/10">
              <Sparkles className="size-6 text-primary" />
            </div>
            <h2 className="mt-5 text-[22px] font-semibold text-foreground">临时会话</h2>
            <p className="mt-1.5 text-[14px] text-muted-foreground">
              从这里快速探索、生成和试跑想法。首次发送成功后才会创建正式会话。
            </p>

            <div className="mt-4 rounded-full border border-border bg-card px-4 py-2 text-[12px] text-muted-foreground">
              当前模式 <span className="font-medium text-foreground">{currentModeOption.label}</span>
              <span className="mx-2 text-border">/</span>
              {currentModeOption.description}
            </div>

            <div className="mt-8 w-full max-w-[560px]">
              <p className="mb-3 text-[13px] font-medium text-muted-foreground">快速开始</p>
              <div className="grid gap-2 sm:grid-cols-2">
                {QUICK_PROMPTS.map((prompt) => (
                  <button
                    key={prompt}
                    onClick={() => setInput(prompt)}
                    className="rounded-lg border border-border bg-card px-4 py-3 text-left text-[13px] text-foreground transition-colors hover:bg-accent"
                  >
                    {prompt}
                  </button>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <div className="mx-auto flex w-full max-w-[760px] flex-col gap-4 px-6 py-6">
            {messages.map((message) => (
              <MessageBubble
                key={message.id}
                message={message}
                thinking={runtime.thinkingByMessageId[message.id]}
              />
            ))}
            {isLoading && messages.every((m) => m.role !== "assistant") && (
              <div className="flex justify-start">
                <div className="flex items-center gap-2 rounded-lg border border-border bg-card px-4 py-3">
                  <Loader2 className="size-4 animate-spin" />
                  <span className="text-[14px] text-muted-foreground">正在生成回复</span>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Pinned bottom: status bar + composer */}
      <div className="mx-auto w-full max-w-[760px] px-6 pb-5">
        {(runtime.phase !== "idle" || error) && (
          <div className="mb-3 rounded-lg border border-border bg-secondary/50 px-4 py-2.5">
            <div className="flex items-center justify-between">
              <p className="text-[13px] text-muted-foreground">{error || runtime.label}</p>
              <Badge variant="outline" className={cn("text-[11px]", statusTone(runtime.phase))}>
                {statusLabel(runtime.phase)}
              </Badge>
            </div>
          </div>
        )}

        <div className="rounded-xl border border-border bg-card shadow-sm">
          <Textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                void handleSubmit();
              }
            }}
            placeholder="输入问题或任务..."
            className="min-h-[100px] resize-none border-none bg-transparent px-5 py-4 text-[15px] focus-visible:ring-0"
            disabled={isLoading}
          />
          <div className="flex items-center justify-between border-t border-border px-4 py-2.5">
            <div className="flex items-center gap-1">
              <ModePicker selected={selectedMode} onSelect={setSelectedMode} />
              <Button variant="ghost" size="icon-xs" disabled className="text-muted-foreground" title="上传附件">
                <Paperclip className="size-4" />
              </Button>
              {lastAssistantMessage && (
                <Button
                  variant="ghost"
                  size="icon-xs"
                  className="text-muted-foreground"
                  onClick={() => navigator.clipboard.writeText(lastAssistantMessage.content)}
                  title="复制回复"
                >
                  <Copy className="size-4" />
                </Button>
              )}
            </div>
            <div className="flex items-center gap-1.5">
              <ModelPicker selected={selectedModel} onSelect={setSelectedModel} />
              <Button
                onClick={() => void handleSubmit()}
                disabled={!input.trim() || isLoading}
                size="icon-sm"
                className="rounded-lg"
              >
                {isLoading ? <Loader2 className="size-4 animate-spin" /> : <ArrowUp className="size-4" />}
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
