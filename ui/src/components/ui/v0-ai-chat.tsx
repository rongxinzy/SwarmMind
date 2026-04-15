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
} from "@/core/chat/types";

export type { ConversationRecord } from "@/core/chat/types";

interface V0ChatProps {
  conversationId?: string;
  draftResetToken?: number;
  onConversationCreated?: (id: string) => void;
  onConversationsChange?: (items: ConversationRecord[]) => void;
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

      const timeoutId = setTimeout(() => {
        abortController.abort();
      }, 30_000);

      try {
        await consumeNdjsonStream<StreamEvent>(
          response.body,
          handleStreamEvent,
          (rawLine, error) => {
            console.warn("[stream] Failed to parse line:", rawLine, error);
          },
        );
      } finally {
        clearTimeout(timeoutId);
      }
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
            <ChatEmptyState
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
        error={error}
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
