"use client";

import type { ChangeEvent, KeyboardEvent } from "react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { ArrowDown } from "lucide-react";

import { Button } from "@/components/ui/button";
import { ArtifactsProvider } from "@/components/workspace/artifacts/context";
import { ChatComposerPanel } from "@/components/workspace/chat-composer-panel";
import { ChatEmptyState } from "@/components/workspace/chat-empty-state";
import { ChatLayout } from "@/components/workspace/chat-layout";
import { MessageListSkeleton } from "@/components/workspace/chat-message-ui";
import { ChatMessageArea } from "@/components/workspace/chat-message-area";
import { SubtasksProvider, useUpdateSubtask, useSubtaskContext } from "@/core/tasks/context";
import { isNearBottom, scrollContainerToLatest } from "@/core/chat/scroll";
import { consumeNdjsonStream } from "@/core/chat/stream";
import { classifyError } from "@/core/chat/mode-config";
import type {
  ChatMessage,
  ConversationMode,
  ConversationRecord,
  RuntimeActivity,
  RuntimeModelCatalogResponse,
  RuntimeModelOption,
  RuntimeState,
  StoredMessage,
  StreamEvent,
  StreamStatus,
  StreamStep,
  ChatError,
} from "@/core/chat/types";

export type { ConversationRecord } from "@/core/chat/types";

interface V0ChatProps {
  conversationId?: string;
  draftResetToken?: number;
  onConversationCreated?: (id: string) => void;
  onConversationsChange?: (items: ConversationRecord[]) => void;
  initialLoading?: boolean;
}

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

// Internal component that uses useUpdateSubtask (must be inside SubtasksProvider)
function V0ChatInner({
  conversationId,
  draftResetToken,
  onConversationCreated,
  onConversationsChange,
  initialLoading = false,
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
  const [isConversationLoading, setIsConversationLoading] = useState(initialLoading);
  const [modelLoadError, setModelLoadError] = useState<string | null>(null);
  const [chatError, setChatError] = useState<ChatError | null>(null);
  const [streamStatus, setStreamStatus] = useState<StreamStatus>(null);
  const [streamStep, setStreamStep] = useState<StreamStep | null>(null);
  const [streamLabel, setStreamLabel] = useState<string | null>(null);
  const [lastUserMessage, setLastUserMessage] = useState<string>("");
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

  // Artifacts state (simplified from DeerFlow)
  const [artifacts, setArtifacts] = useState<string[]>([]);
  const [selectedArtifact, setSelectedArtifact] = useState<string | null>(null);
  const [artifactsOpen, setArtifactsOpen] = useState(false);

  const resetDraftState = useCallback(() => {
    setCurrentConversationId(undefined);
    setMessages([]);
    setAttachedFiles([]);
    setRuntime(createEmptyRuntime());
    setIsConversationLoading(false);
    setChatError(null);
    setStreamStatus(null);
    setStreamStep(null);
    setStreamLabel(null);
    setInput("");
    setSelectedMode(DEFAULT_MODE);
    setPendingClarification(null);
    setSelectedModel(defaultModel);
    shouldStickToBottomRef.current = true;
    setShowScrollToLatest(false);
    setArtifacts([]);
    setArtifactsOpen(false);
    setSelectedArtifact(null);
  }, [defaultModel]);

  const syncScrollState = useCallback(() => {
    const container = scrollContainerRef.current;
    if (!container) {
      return;
    }

    const nextIsNearBottom = isNearBottom(container);
    shouldStickToBottomRef.current = nextIsNearBottom;
    setShowScrollToLatest(!nextIsNearBottom);
  }, []);

  const scrollToLatest = useCallback((behavior: ScrollBehavior = "smooth") => {
    const container = scrollContainerRef.current;
    if (!container) {
      return;
    }
    scrollContainerToLatest(container, behavior);
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
    setChatError(null);
    setStreamStatus(null);
    setStreamStep(null);
    setStreamLabel(null);
    setInput("");
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
      const errorType = classifyError(requestError);
      setChatError({
        type: errorType,
        message: requestError instanceof Error ? requestError.message : "加载会话失败",
        retryCount: 0,
      });
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
      // Sync URL without remounting
      window.history.replaceState(null, "", `/?conversation=${record.id}`);
      return record.id;
    },
    [onConversationCreated],
  );

  const clearStreamIndicators = useCallback(() => {
    setStreamStatus(null);
    setStreamStep(null);
    setStreamLabel(null);
  }, []);

  const handleStreamEvent = useCallback((event: StreamEvent) => {
    console.log("[DEBUG] Stream event received:", event.type, event);
    switch (event.type) {
      case "status":
        setRuntime((previous) => ({
          ...previous,
          phase: event.phase,
          label: event.label,
        }));
        if (event.phase === "routing") {
          setStreamStatus("thinking");
        } else if (event.phase === "running") {
          setStreamStatus("running");
        } else if (event.phase === "completed" || event.phase === "error") {
          setIsLoading(false);
          setStreamStatus(null);
          setStreamStep(null);
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
        if (typeof event.step === "number") {
          setStreamStep({
            step: event.step,
            totalSteps: typeof event.total_steps === "number" ? event.total_steps : undefined,
          });
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
        setStreamStatus("thinking");
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
        setStreamStatus("running");
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
        clearStreamIndicators();
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
        setStreamStatus("running");
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
        setStreamStatus("running");
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
        setStreamStatus("clarification");
        setPendingClarification({
          id: event.clarification.id,
          content: event.clarification.content,
        });
        return;

      case "artifact":
        setStreamStatus("artifact");
        setArtifacts((prev) => {
          if (prev.includes(event.path)) return prev;
          return [...prev, event.path];
        });
        setArtifactsOpen(true);
        return;

      // New SSE semantic layer events
      case "status.thinking":
        setStreamStatus("thinking");
        if (event.text) {
          setStreamLabel(event.text);
          // Also update the active assistant message's thinking field so
          // MessageBubble can render the reasoning panel in real time.
          setMessages((previous) => {
            const activeAssistantIndex = findActiveAssistantIndex(previous);
            if (activeAssistantIndex !== -1) {
              const next = [...previous];
              next[activeAssistantIndex] = {
                ...next[activeAssistantIndex],
                thinking: event.text,
                isReasoningStreaming: true,
              };
              return next;
            }
            return [
              ...previous,
              {
                id: `thinking-${generateId()}`,
                role: "assistant",
                content: "",
                thinking: event.text,
                isStreaming: false,
                isReasoningStreaming: true,
              },
            ];
          });
        }
        return;

      case "status.running":
        setStreamStatus("running");
        if (typeof event.step === "number") {
          setStreamStep({
            step: event.step,
            totalSteps: typeof event.total_steps === "number" ? event.total_steps : undefined,
          });
        }
        return;

      case "status.clarification":
        setStreamStatus("clarification");
        setPendingClarification({
          id: `clarification-${generateId()}`,
          content: event.question,
        });
        return;

      case "status.artifact":
        setStreamStatus("artifact");
        if (event.name) {
          setArtifacts((prev) => {
            if (prev.includes(event.name!)) return prev;
            return [...prev, event.name!];
          });
          setArtifactsOpen(true);
        }
        return;

      case "content.accumulated":
        setStreamStatus("running");
        setMessages((previous) => {
          const activeAssistantIndex = findActiveAssistantIndex(previous);
          if (activeAssistantIndex !== -1) {
            const next = [...previous];
            next[activeAssistantIndex] = {
              ...next[activeAssistantIndex],
              content: event.text,
              isStreaming: true,
              isReasoningStreaming: false,
            };
            return next;
          }
          return [
            ...previous,
            {
              id: `delta-${generateId()}`,
              role: "assistant",
              content: event.text,
              isStreaming: true,
              isReasoningStreaming: false,
            },
          ];
        });
        return;

      case "error":
        setIsLoading(false);
        clearStreamIndicators();
        setChatError({
          type: "server",
          message: event.message,
          retryCount: 0,
        });
        setRuntime((previous) => ({
          ...previous,
          phase: "error",
          label: `执行失败：${event.message}`,
        }));
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
        return;

      case "done":
        setIsLoading(false);
        clearStreamIndicators();
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
  }, [updateSubtask, clearStreamIndicators]);

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

      await consumeNdjsonStream<StreamEvent>(
        response.body,
        handleStreamEvent,
        (rawLine, error) => {
          console.warn("[stream] Failed to parse line:", rawLine, error);
        },
      );
    },
    [handleStreamEvent],
  );

  const handleFileSelect = useCallback((e: ChangeEvent<HTMLInputElement>) => {
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
        const errorType = classifyError(modelLoadError ?? new Error("当前未分配可用模型"));
        setChatError({
          type: errorType,
          message: modelLoadError ?? "当前未分配可用模型，无法发起会话",
          retryCount: 0,
        });
        return;
      }

      if (!prompt) setInput("");
      setAttachedFiles([]);

      setChatError(null);
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
      setStreamStatus(null);
      setStreamStep(null);
      setStreamLabel(null);
      setLastUserMessage(text);

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
        // 忽略主动取消（如切换会话、组件卸载导致的 abort）
        if (
          requestError instanceof DOMException &&
          requestError.name === "AbortError"
        ) {
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
          return;
        }
        const errorType = classifyError(requestError);
        const message =
          requestError instanceof Error
            ? requestError.message
            : "发送消息时发生未知错误";
        setChatError((prev) => ({
          type: errorType,
          message,
          retryCount: prev?.retryCount ?? 0,
        }));
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

  const handleRetry = useCallback(async () => {
    if (!lastUserMessage || isLoading) return;
    const nextRetryCount = (chatError?.retryCount ?? 0) + 1;
    setChatError((prev) =>
      prev ? { ...prev, retryCount: nextRetryCount } : null,
    );
    await handleSubmit(lastUserMessage);
  }, [lastUserMessage, isLoading, chatError?.retryCount, handleSubmit]);

  const handleCopyQuestion = useCallback(() => {
    if (lastUserMessage) {
      void navigator.clipboard.writeText(lastUserMessage);
    }
  }, [lastUserMessage]);

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
        setChatError(null);
        setRuntime((prev) => ({
          ...prev,
          phase: "running",
          label: "正在继续处理...",
        }));
        setStreamStatus("running");

        // Resume streaming - the backend will pick up from where it left off
        await streamConversation(
          currentConversationId,
          response,
          selectedMode,
          selectedModel
        );
      } catch (err) {
        console.error("Failed to send clarification response:", err);
        if (err instanceof DOMException && err.name === "AbortError") {
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
          setIsLoading(false);
          return;
        }
        const errorType = classifyError(err);
        setChatError({
          type: errorType,
          message: err instanceof Error ? err.message : "发送回复失败",
          retryCount: 0,
        });
        setIsLoading(false);
      }
    },
    [currentConversationId, selectedMode, selectedModel, streamConversation]
  );

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
            <ChatEmptyState
              isDraft={!currentConversationId}
              onPromptSelect={(prompt) => {
                setInput(prompt);
                void handleSubmit(prompt);
              }}
            />
          ) : (
            <ChatMessageArea
              isLoading={isLoading}
              messages={messages}
              pendingClarification={pendingClarification}
              tasks={tasks}
              onClarificationRespond={handleClarificationRespond}
              onPendingClarificationHandled={() => {
                setPendingClarification(null);
              }}
              error={chatError}
              onRetry={handleRetry}
              onCopy={handleCopyQuestion}
              isRetrying={isLoading}
            />
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

      <ChatComposerPanel
        attachedFiles={attachedFiles}
        error={chatError}
        fetchModels={() => {
          void fetchModels();
        }}
        fileInputRef={fileInputRef}
        handleFileSelect={handleFileSelect}
        handleRemoveFile={handleRemoveFile}
        handleSubmit={() => {
          void handleSubmit();
        }}
        input={input}
        isComposerDisabled={isComposerDisabled}
        isLoading={isLoading}
        isModelsLoading={isModelsLoading}
        lastAssistantMessage={lastAssistantMessage}
        modelLoadError={modelLoadError}
        modelOptions={modelOptions}
        onInputChange={setInput}
        onKeyDown={(e: KeyboardEvent<HTMLTextAreaElement>) => {
          if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            void handleSubmit();
          }
        }}
        runtime={runtime}
        selectedMode={selectedMode}
        selectedModel={selectedModel}
        setSelectedMode={setSelectedMode}
        setSelectedModel={setSelectedModel}
        streamStatus={streamStatus}
        streamStep={streamStep}
        streamLabel={streamLabel}
      />
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
