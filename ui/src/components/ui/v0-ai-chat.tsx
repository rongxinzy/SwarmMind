"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  ArrowDown,
  ArrowUp,
  Brain,
  Check,
  Copy,
  Lightbulb,
  Loader2,
  Paperclip,
  Rocket,
  Sparkles,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { ArtifactsProvider } from "@/components/workspace/artifacts/context";
import { ChatLayout } from "@/components/workspace/chat-layout";
import { MessageBubble, MessageListSkeleton, StreamingDots } from "@/components/workspace/chat-message-ui";
import { ClarificationCard } from "@/components/workspace/messages/clarification-card";
import { ModePicker, ModelPicker } from "@/components/workspace/chat-controls";
import { SubtasksProvider, useUpdateSubtask, useSubtaskContext } from "@/core/tasks/context";
import { SubtaskCard } from "@/components/workspace/messages/subtask-card";
import { parseClarificationContent } from "@/core/messages/clarification";
import { cn } from "@/lib/utils";
import { XIcon } from "lucide-react";
import { toast } from "sonner";

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
  | { type: "artifact"; path: string; filename?: string }
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

const DEFAULT_MODE: ConversationMode = "flash";
const DEFAULT_MODEL = "";

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

// Internal component that uses useUpdateSubtask (must be inside SubtasksProvider)
function V0ChatInner({
  conversationId,
  draftResetToken,
  onConversationCreated,
  onConversationsChange,
}: V0ChatProps) {
  const updateSubtask = useUpdateSubtask();
  const { tasks } = useSubtaskContext();

  // Debug: monitor tasks changes
  useEffect(() => {
    const taskCount = Object.values(tasks).length;
    if (taskCount > 0) {
      console.log("[DEBUG] Tasks updated:", tasks);
    }
  }, [tasks]);

  const [conversations, setConversations] = useState<ConversationRecord[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [runtime, setRuntime] = useState<RuntimeState>(createEmptyRuntime());
  const [input, setInput] = useState("");
  const [attachedFiles, setAttachedFiles] = useState<File[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);
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
  const streamAbortRef = useRef<AbortController | null>(null);
  const [showScrollToLatest, setShowScrollToLatest] = useState(false);
  
  // Clarification request state
  const [pendingClarification, setPendingClarification] = useState<
    { id: string; content: string } | null
  >(null);

  const resetDraftState = useCallback(() => {
    setCurrentConversationId(undefined);
    setMessages([]);
    setAttachedFiles([]);
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

        setModelLoadError(`模型加载重试中 (${attempt}/${MODEL_FETCH_RETRY_COUNT})...`);
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
    streamAbortRef.current?.abort();
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

    return () => { window.clearTimeout(retryTimer); };
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
      return () => { window.cancelAnimationFrame(rafId); };
    }

    const rafId = window.requestAnimationFrame(() => {
      scrollToLatest(messages.length > 0 ? "smooth" : "auto");
    });
    return () => { window.cancelAnimationFrame(rafId); };
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
    console.log("[DEBUG] Stream event received:", event.type, event);
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
        if (event.phase === "completed") {
          setTimeout(() => {
            setRuntime((prev) => ({ ...prev, activities: [] }));
          }, 2000);
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
        console.log("[DEBUG] task_started event received:", event.task);
        updateSubtask({
          id: event.task.id,
          description: event.task.description,
          status: "in_progress",
          subagent_type: "general-purpose",
          prompt: "",
        });
        console.log("[DEBUG] updateSubtask called for task_started");
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

      case "artifact":
        setArtifacts((prev) => {
          if (prev.includes(event.path)) return prev;
          return [...prev, event.path];
        });
        setArtifactsOpen(true);
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
      streamAbortRef.current?.abort();
      const abortController = new AbortController();
      streamAbortRef.current = abortController;

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
          signal: abortController.signal,
        },
      );

      if (!response.ok || !response.body) {
        throw new Error(`HTTP ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      const timeoutId = setTimeout(() => {
        abortController.abort();
      }, 30_000);

      try {
        // eslint-disable-next-line no-constant-condition
        while (true) {
          const { value, done } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          let lineBreakIndex = buffer.indexOf("\n");
          while (lineBreakIndex >= 0) {
            const rawLine = buffer.slice(0, lineBreakIndex).trim();
            buffer = buffer.slice(lineBreakIndex + 1);

            if (rawLine) {
              try {
                handleStreamEvent(JSON.parse(rawLine) as StreamEvent);
              } catch (e) {
                console.warn("[stream] Failed to parse line:", rawLine, e);
              }
            }

            lineBreakIndex = buffer.indexOf("\n");
          }
        }

        const lastLine = buffer.trim();
        if (lastLine) {
          try {
            handleStreamEvent(JSON.parse(lastLine) as StreamEvent);
          } catch (e) {
            console.warn("[stream] Failed to parse line:", lastLine, e);
          }
        }
      } finally {
        clearTimeout(timeoutId);
      }
    },
    [handleStreamEvent],
  );

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files ?? []);
    if (files.length === 0) return;
    setAttachedFiles((prev) => {
      const existing = new Set(prev.map((f) => f.name + f.size));
      return [...prev, ...files.filter((f) => !existing.has(f.name + f.size))];
    });
    // Reset input so same file can be re-selected
    if (fileInputRef.current) fileInputRef.current.value = "";
  }, []);

  const handleRemoveFile = useCallback((index: number) => {
    setAttachedFiles((prev) => prev.filter((_, i) => i !== index));
  }, []);

  const handleSubmit = useCallback(
    async (prompt?: string) => {
      const text = (prompt ?? input).trim();
      if (!text || isLoading) return;
      if (!selectedModel) {
        setError(modelLoadError ?? "当前未分配可用模型，无法发起会话");
        return;
      }

      if (!prompt) setInput("");
      setAttachedFiles([]);

      setError(null);
      setIsLoading(true);
      setPendingClarification(null); // Clear any pending clarification when sending new message
      setArtifacts([]);
      setArtifactsOpen(false);
      setSelectedArtifact(null);
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
  const [artifacts, setArtifacts] = useState<string[]>([]);
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
                  <div className="inline-flex size-10 items-center justify-center rounded-xl border bg-[var(--warm-ivory)] text-[var(--neutral-600)]"
                    style={{ boxShadow: 'var(--shadow-whisper)' }}
                  >
                    <Sparkles className="size-4" />
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
                      className="group flex items-start gap-3 rounded-xl border bg-[var(--warm-ivory)] px-4 py-3.5 text-left transition-all duration-200 hover:border-[var(--warm-ring)] hover:bg-[var(--neutral-150)]"
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
                  // Try to parse as clarification if message looks like it
                  if (
                    message.role === "assistant" &&
                    (message.content.includes("需要") ||
                     message.content.includes("?") ||
                     message.content.includes("选择") ||
                     message.content.includes("确认"))
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
                    } catch (e) {
                      toast.error("AI 澄清请求解析失败，请查看原始消息");
                      console.warn("[clarification] parse failed:", e);
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
                    try {
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
                    } catch (e) {
                      toast.error("AI 澄清请求解析失败，请查看原始消息");
                      console.warn("[clarification] parse failed:", e);
                      return null;
                    }
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
                    <div className="flex items-center gap-2 rounded-xl border border-[var(--warm-border)] bg-[var(--neutral-150)] px-4 py-2">
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
                onClick={() => { scrollToLatest("smooth"); }}
                aria-label="回到最新"
                title="回到最新"
                className="pointer-events-auto size-10 rounded-full border-[var(--warm-border)] bg-[var(--warm-ivory)] hover:bg-[var(--neutral-150)] hover:border-[var(--warm-ring)]"
                style={{ boxShadow: 'var(--shadow-whisper)' }}
              >
                <ArrowDown className="size-3.5" />
              </Button>
            </motion.div>
          ) : null}
        </AnimatePresence>
      </div>

      {/* Pinned bottom: status + composer as unified container */}
      <div className="sticky bottom-0 z-20"
        style={{
          background: 'linear-gradient(to top, var(--warm-paper) 0%, var(--warm-paper) 85%, transparent 100%)',
        }}
      >
        <div className="relative border-t border-[var(--warm-border)]/50 bg-[var(--warm-paper)]">
          <div className="mx-auto w-full max-w-[760px] px-6 pb-5 pt-2.5">
            <div
              className="rounded-2xl border border-[var(--warm-border)] bg-[var(--warm-ivory)] transition-all duration-200 focus-within:border-[var(--warm-ring)]"
              style={{
                boxShadow: 'var(--shadow-whisper)',
              }}
            >
              {(runtime.phase !== "idle" || error) && (
                <div
                  className="border-b border-[var(--warm-border)] bg-[var(--neutral-150)] px-5 py-2.5"
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
                        <div
                          key={activity.id}
                          className="flex items-center gap-2 text-xs"
                        >
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
                                : "text-[var(--neutral-500)]"
                            )}
                          >
                            {activity.label}
                          </span>
                          {activity.detail && (
                            <span className="ml-auto shrink-0 text-[var(--neutral-400)] max-w-[120px] truncate">
                              {activity.detail}
                            </span>
                          )}
                        </div>
                      ))}
                      {runtime.activities.length > 5 && (
                        <p className="text-xs text-[var(--neutral-400)] pl-5">
                          +{runtime.activities.length - 5} 个任务...
                        </p>
                      )}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>

              <div>
                {attachedFiles.length > 0 && (
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
                )}
                <Textarea
                  value={input}
                  onChange={(e) => { setInput(e.target.value); }}
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
                <div className="flex flex-col gap-2 border-t border-[var(--warm-border)] bg-[var(--neutral-150)]/70 px-4 py-2.5 sm:flex-row sm:items-center sm:justify-between">
                  <div className="flex flex-wrap items-center gap-2">
                    <ModePicker
                      selected={selectedMode}
                      onSelect={setSelectedMode}
                    />
                    <>
                      <input
                        ref={fileInputRef}
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
                    {lastAssistantMessage && (
                      <Button
                        variant="ghost"
                        size="icon-sm"
                        className="size-10 rounded-lg border border-transparent text-[var(--neutral-600)] hover:border-[var(--warm-border)] hover:bg-[var(--warm-ivory)]"
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
