"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import {
  Bot,
  Brain,
  Calendar,
  FolderOpen,
  Loader2,
  Plus,
  Send,
  Sparkles,
  Upload,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface V0ChatProps {
  conversationId?: string;
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

const QUICK_CHIPS = [
  { label: "CRM MVP 范围", prompt: "帮我梳理 CRM MVP 的模块边界，并判断是否应该立项。" },
  { label: "竞品调研", prompt: "做一轮简洁的竞品调研，帮我列出差异点和风险。" },
  { label: "招聘自动化", prompt: "招聘流程自动化第一版应该优先覆盖哪些环节？" },
  { label: "续费风险", prompt: "请分析我们当前客户续费风险最高的信号有哪些。" },
];

const CAPABILITIES = [
  {
    title: "流式会话",
    description: "回答按运行过程持续更新，不等最后一次性返回。",
  },
  {
    title: "Thinking",
    description: "当模型提供推理内容时，在当前工作面内展开查看。",
  },
  {
    title: "协作状态",
    description: "展示 Agent Team 的分工、工具执行和进度变化。",
  },
];

function generateId() {
  return Math.random().toString(36).slice(2, 10);
}

function createEmptyRuntime(): RuntimeState {
  return {
    phase: "idle",
    label: "准备开始新的探索会话",
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
        title: patch.title ?? "新的协作分工",
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
  if (phase === "routing" || phase === "running" || phase === "accepted") {
    return "status-pill-running";
  }
  return "status-pill-chat";
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
          isUser
            ? "border-primary bg-primary text-primary-foreground"
            : "border-border bg-card text-foreground",
        )}
      >
        {!isUser && thinking ? (
          <details className="mb-3 rounded-md border border-border bg-muted/40 px-3 py-2">
            <summary className="flex cursor-pointer list-none items-center gap-2 text-xs text-muted-foreground">
              <Brain className="size-3.5" />
              模型思考
            </summary>
            <div className="mt-2 whitespace-pre-wrap text-xs leading-6 text-muted-foreground">
              {thinking}
            </div>
          </details>
        ) : null}

        {message.content ? (
          isUser ? (
            <div className="whitespace-pre-wrap text-sm leading-7">{message.content}</div>
          ) : (
            <div className="prose prose-sm max-w-none text-sm leading-7 dark:prose-invert">
              <ReactMarkdown>{message.content}</ReactMarkdown>
            </div>
          )
        ) : (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="size-4 animate-spin" />
            正在整理回答
          </div>
        )}
      </div>
    </div>
  );
}

function EmptyHero({
  onFillPrompt,
}: {
  onFillPrompt: (prompt: string) => void;
}) {
  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col items-center px-4 py-16 text-center">
      <Badge variant="outline" className="status-pill-chat rounded-full px-3 py-1">
        临时 ChatSession
      </Badge>
      <h2 className="mt-6 text-3xl font-semibold tracking-tight text-foreground">
        先发起一次探索，再决定是否提升为 Project
      </h2>
      <p className="mt-3 max-w-2xl text-sm leading-7 text-muted-foreground">
        这里优先承接临时会话。系统会在当前工作面持续展示运行状态、思考信息和 Agent Team
        协作过程。
      </p>

      <div className="mt-8 flex flex-wrap justify-center gap-2">
        {QUICK_CHIPS.map((chip) => (
          <Button
            key={chip.label}
            variant="outline"
            size="sm"
            className="rounded-full"
            onClick={() => onFillPrompt(chip.prompt)}
          >
            {chip.label}
          </Button>
        ))}
      </div>

      <div className="mt-10 grid w-full gap-3 md:grid-cols-3">
        {CAPABILITIES.map((capability) => (
          <Card key={capability.title}>
            <CardHeader>
              <CardTitle className="text-sm">{capability.title}</CardTitle>
            </CardHeader>
            <CardContent className="pt-4">
              <p className="text-sm leading-6 text-muted-foreground">{capability.description}</p>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

function RuntimePanel({ runtime }: { runtime: RuntimeState }) {
  const thinkingEntries = Object.entries(runtime.thinkingByMessageId).filter(([, content]) =>
    Boolean(content.trim()),
  );

  return (
    <div className="flex h-full flex-col gap-4">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between gap-3">
            <div>
              <CardTitle className="text-sm">当前运行</CardTitle>
              <CardDescription className="mt-1 text-xs leading-5">
                运行态直接对齐 deer-flow 的流式过程，但界面保留 SwarmMind 自己的产品语义。
              </CardDescription>
            </div>
            <Badge variant="outline" className={cn("rounded-full px-2.5", statusTone(runtime.phase))}>
              {runtime.phase === "idle" ? "待开始" : runtime.phase}
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="pt-4">
          <div className="rounded-lg border bg-muted/30 p-3">
            <p className="text-xs font-medium text-muted-foreground">Status</p>
            <p className="mt-2 text-sm leading-6 text-foreground">{runtime.label}</p>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Agent Team 协作</CardTitle>
          <CardDescription>不暴露 sub-agent 术语，统一翻译为用户可理解的协作分工。</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-3 pt-4">
          {runtime.tasks.length === 0 ? (
            <div className="rounded-lg border border-dashed bg-muted/20 p-4 text-sm leading-6 text-muted-foreground">
              当前还没有新的协作分工。复杂问题进入多步骤处理后，会在这里出现 Team 内部分工。
            </div>
          ) : (
            runtime.tasks.map((task) => (
              <div key={task.id} className="rounded-lg border bg-background p-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-sm font-medium text-foreground">{task.title}</p>
                    {task.detail ? (
                      <p className="mt-2 text-sm leading-6 text-muted-foreground">{task.detail}</p>
                    ) : null}
                  </div>
                  <Badge
                    variant="outline"
                    className={cn(
                      "rounded-full px-2.5",
                      task.status === "failed"
                        ? "status-pill-blocked"
                        : task.status === "completed"
                          ? "status-pill-done"
                          : "status-pill-running",
                    )}
                  >
                    {task.status === "running"
                      ? "进行中"
                      : task.status === "completed"
                        ? "已完成"
                        : "失败"}
                  </Badge>
                </div>
              </div>
            ))
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">运行活动</CardTitle>
          <CardDescription>工具调用、资料读取和外部检索会作为活动流显示在这里。</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-3 pt-4">
          {runtime.activities.length === 0 ? (
            <div className="rounded-lg border border-dashed bg-muted/20 p-4 text-sm leading-6 text-muted-foreground">
              当前没有新的运行活动。
            </div>
          ) : (
            runtime.activities.map((activity) => (
              <div key={activity.id} className="rounded-lg border bg-background p-4">
                <div className="flex items-center justify-between gap-3">
                  <p className="text-sm font-medium text-foreground">{activity.label}</p>
                  <Badge
                    variant="outline"
                    className={cn(
                      "rounded-full px-2.5",
                      activity.status === "completed"
                        ? "status-pill-done"
                        : "status-pill-running",
                    )}
                  >
                    {activity.status === "completed" ? "完成" : "执行中"}
                  </Badge>
                </div>
                {activity.detail ? (
                  <p className="mt-2 text-sm leading-6 text-muted-foreground">{activity.detail}</p>
                ) : null}
              </div>
            ))
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Thinking</CardTitle>
          <CardDescription>如果模型返回推理内容，会在这里和消息气泡内同时可见。</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-3 pt-4">
          {thinkingEntries.length === 0 ? (
            <div className="rounded-lg border border-dashed bg-muted/20 p-4 text-sm leading-6 text-muted-foreground">
              当前没有可展示的 thinking 内容。
            </div>
          ) : (
            thinkingEntries.map(([messageId, content]) => (
              <div key={messageId} className="rounded-lg border bg-background p-4">
                <div className="flex items-center gap-2 text-xs font-medium text-muted-foreground">
                  <Brain className="size-3.5" />
                  Thinking
                </div>
                <div className="mt-3 whitespace-pre-wrap text-sm leading-6 text-muted-foreground">
                  {content}
                </div>
              </div>
            ))
          )}
        </CardContent>
      </Card>
    </div>
  );
}

export function V0Chat({ conversationId, onConversationCreated, onConversationsChange }: V0ChatProps) {
  const [conversations, setConversations] = useState<ConversationRecord[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [runtime, setRuntime] = useState<RuntimeState>(createEmptyRuntime());
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentConversationId, setCurrentConversationId] = useState<string | undefined>(conversationId);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

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

    setCurrentConversationId(undefined);
    setMessages([]);
    setRuntime(createEmptyRuntime());
    setError(null);
  }, [conversationId, loadMessages]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, runtime]);

  const activeConversation = useMemo(() => {
    if (!currentConversationId) return undefined;
    return conversations.find((conversation) => conversation.id === currentConversationId);
  }, [conversations, currentConversationId]);

  const handleNewConversation = useCallback(() => {
    setCurrentConversationId(undefined);
    setMessages([]);
    setRuntime(createEmptyRuntime());
    setError(null);
    setInput("");
    inputRef.current?.focus();
  }, []);

  const createConversation = useCallback(async () => {
    const response = await fetch("/conversations", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ goal: input.trim() || "新建临时会话" }),
    });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const record = (await response.json()) as ConversationRecord;
    setConversations((previous) => sortConversations([record, ...previous.filter((item) => item.id !== record.id)]));
    setCurrentConversationId(record.id);
    onConversationCreated?.(record.id);
    return record.id;
  }, [input, onConversationCreated]);

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
        return;
    }
  }, []);

  const streamConversation = useCallback(
    async (nextConversationId: string, text: string) => {
      const response = await fetch(`/conversations/${nextConversationId}/messages/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content: text, reasoning: true }),
      });

      if (!response.ok || !response.body) {
        throw new Error(`HTTP ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) {
          break;
        }

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
      if (!text || isLoading) {
        return;
      }

      if (!prompt) {
        setInput("");
      }

      setError(null);
      setIsLoading(true);
      setRuntime({
        ...createEmptyRuntime(),
        phase: "accepted",
        label: "消息已提交，正在准备本轮运行",
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
        const nextConversationId = currentConversationId ?? (await createConversation());
        await streamConversation(nextConversationId, text);
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
    [createConversation, currentConversationId, fetchConversations, input, isLoading, streamConversation],
  );

  const currentTitle = currentConversationId
    ? activeConversation?.title ?? "New Conversation"
    : "新建对话";

  return (
    <div className="flex h-full min-h-0 flex-col bg-background">
      <div className="border-b border-border bg-background px-4 py-4 md:px-6">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="truncate text-xl font-semibold tracking-tight text-foreground">
                {currentTitle}
              </h2>
              {activeConversation?.title_status === "pending" ? (
                <Badge variant="outline" className="status-pill-chat rounded-full px-2.5">
                  标题待生成
                </Badge>
              ) : null}
            </div>
            <p className="mt-1 text-sm text-muted-foreground">
              临时 ChatSession 用于探索、提问和快速验证；需要共享、审批和治理时再提升为
              Project。
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <Button variant="outline" size="lg" onClick={handleNewConversation} className="gap-2">
              <Plus className="size-4" />
              新建对话
            </Button>
            <Button variant="outline" size="lg" className="gap-2" disabled>
              <Upload className="size-4" />
              上传资料
            </Button>
            <Button size="lg" className="gap-2" disabled={!currentConversationId}>
              <Sparkles className="size-4" />
              提升为 Project
            </Button>
          </div>
        </div>
      </div>

      <div className="grid min-h-0 flex-1 gap-4 p-4 xl:grid-cols-[minmax(0,1fr)_360px] md:p-6">
        <main className="min-h-0">
          <Card className="flex h-full">
            <CardHeader>
              <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                <div className="flex items-center gap-2">
                  <Bot className="size-4 text-muted-foreground" />
                  <div>
                    <CardTitle className="text-sm">主会话面</CardTitle>
                    <CardDescription>
                      主消息流承接探索问题；运行细节与协作状态留在同一工作面，而不是跳页查看。
                    </CardDescription>
                  </div>
                </div>
                <Badge variant="outline" className={cn("rounded-full px-2.5", statusTone(runtime.phase))}>
                  {runtime.label}
                </Badge>
              </div>
            </CardHeader>

            <CardContent className="flex min-h-0 flex-1 flex-col px-0 pt-0">
              <div className="min-h-0 flex-1 overflow-y-auto px-4 py-6 md:px-6">
                {messages.length === 0 && !isLoading ? (
                  <EmptyHero onFillPrompt={(prompt) => setInput(prompt)} />
                ) : (
                  <div className="mx-auto flex w-full max-w-3xl flex-col gap-4">
                    {messages.map((message) => (
                      <MessageBubble
                        key={message.id}
                        message={message}
                        thinking={runtime.thinkingByMessageId[message.id]}
                      />
                    ))}
                    {isLoading && messages.every((message) => message.role !== "assistant") ? (
                      <div className="flex justify-start">
                        <div className="flex items-center gap-2 rounded-lg border border-border bg-card px-4 py-3 text-sm text-muted-foreground">
                          <Loader2 className="size-4 animate-spin" />
                          Agent Team 正在整理第一条回复
                        </div>
                      </div>
                    ) : null}
                    <div ref={messagesEndRef} />
                  </div>
                )}
              </div>

              <div className="border-t border-border px-4 py-4 md:px-6">
                <div className="mx-auto flex w-full max-w-3xl flex-col gap-3">
                  {error ? (
                    <div className="rounded-lg border border-destructive/50 bg-destructive/10 px-4 py-3 text-sm text-destructive">
                      {error}
                    </div>
                  ) : null}

                  <div className="rounded-lg border border-border bg-background p-3">
                    <textarea
                      ref={inputRef}
                      value={input}
                      onChange={(event) => setInput(event.target.value)}
                      onKeyDown={(event) => {
                        if (event.key === "Enter" && !event.shiftKey) {
                          event.preventDefault();
                          void handleSubmit();
                        }
                      }}
                      placeholder="描述你的问题、目标或临时任务。系统会直接在当前工作面展示 thinking 与协作状态。"
                      className="min-h-[120px] w-full resize-none border-none bg-transparent px-1 py-1 text-sm leading-7 text-foreground outline-none placeholder:text-muted-foreground"
                      disabled={isLoading}
                    />

                    <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-border pt-3">
                      <Button variant="outline" size="sm" className="gap-1.5 text-muted-foreground">
                        <Upload className="size-3.5" />
                        上传文件
                      </Button>
                      <Button variant="outline" size="sm" className="gap-1.5 text-muted-foreground">
                        <FolderOpen className="size-3.5" />
                        关联项目
                      </Button>
                      <Button variant="outline" size="sm" className="gap-1.5 text-muted-foreground">
                        <Calendar className="size-3.5" />
                        定时执行
                      </Button>

                      <Button
                        onClick={() => void handleSubmit()}
                        disabled={!input.trim() || isLoading}
                        className="ml-auto gap-2 px-4"
                      >
                        {isLoading ? <Loader2 className="size-4 animate-spin" /> : <Send className="size-4" />}
                        {isLoading ? "处理中" : "发送"}
                      </Button>
                    </div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </main>

        <aside className="hidden min-h-0 xl:block">
          <RuntimePanel runtime={runtime} />
        </aside>
      </div>

      <div className="px-4 pb-4 xl:hidden md:px-6">
        <RuntimePanel runtime={runtime} />
      </div>
    </div>
  );
}
