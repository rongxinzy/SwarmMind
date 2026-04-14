import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import {
  BookOpenText,
  Bot,
  Clock3,
  FolderKanban,
  History,
  Library,
  Search,
  Sparkles,
} from "lucide-react";

import { Workbench } from "@/components/workbench";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Sidebar, type SidebarView, VIEW_LABELS } from "@/components/ui/sidebar";
import { V0Chat, type ConversationRecord } from "@/components/ui/v0-ai-chat";
import { cn } from "@/lib/utils";

const viewDescriptions: Record<SidebarView, string> = {
  workbench: "减少选择成本，让用户更快产出结构化结果。",
  chat: "结构化输入、生成、编辑与导出在同一个工作面里完成。",
  teams: "Agent Team 用业务语言表达协作能力，底层配置默认隐藏。",
  skills: "统一管理可用能力、绑定关系和企业范围内的启用状态。",
  assets: "所有正式产物都应该可追溯、可导出、可二次复用。",
  knowledge: "知识访问作为工作流的一部分出现，而不是孤立的技术入口。",
  projects: "项目空间承接执行边界、审批节奏和交付结果。",
  recent: "快速回到最近任务、结果和生成上下文。",
  schedules: "周期性生成、汇总和提醒统一纳入工作流调度。",
};

const viewActions: Record<SidebarView, { primary: string; secondary: string }> =
  {
    workbench: { primary: "新建项目", secondary: "查看审批" },
    chat: { primary: "新建对话", secondary: "查看最近" },
    teams: { primary: "新建 Team", secondary: "查看模板" },
    skills: { primary: "配置能力", secondary: "查看绑定" },
    assets: { primary: "查看产物", secondary: "导出目录" },
    knowledge: { primary: "连接知识源", secondary: "查看权限" },
    projects: { primary: "新建项目", secondary: "查看模板" },
    recent: { primary: "继续任务", secondary: "查看全部" },
    schedules: { primary: "新建任务", secondary: "查看日志" },
  };

function PlaceholderView({
  icon,
  title,
  description,
  action,
}: {
  icon: ReactNode;
  title: string;
  description: string;
  action: string;
}) {
  return (
    <div className="px-4 pb-6 pt-4 md:px-6 md:pb-8">
      <Card>
        <CardHeader className="border-b border-border">
          <div className="flex items-start gap-4">
            <div className="flex size-9 items-center justify-center rounded-md border border-border bg-secondary text-foreground">
              {icon}
            </div>
            <div className="space-y-1.5">
              <CardTitle className="text-[18px] leading-7 tracking-[-0.01em]">{title}</CardTitle>
              <CardDescription>{description}</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="grid gap-4 pt-4 lg:grid-cols-2">
          <div className="rounded-lg border border-border bg-secondary/80 p-4">
            <p className="field-label">模块状态</p>
            <p className="mt-2 text-[14px] leading-[22px] text-muted-foreground">
              当前页面已完成结构定义，下一步会接入真实数据、编辑操作和导出流程。
            </p>
          </div>
          <div className="rounded-lg border border-border bg-card p-4">
            <p className="field-label">下一步</p>
            <div className="mt-3 flex flex-wrap gap-2 pt-1">
              <Button>{action}</Button>
              <Button variant="outline">查看相关文档</Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function PageHeader({
  activeView,
  onPrimaryAction,
  onSecondaryAction,
  searchQuery,
  onSearchQueryChange,
}: {
  activeView: SidebarView;
  onPrimaryAction: () => void;
  onSecondaryAction: () => void;
  searchQuery: string;
  onSearchQueryChange: (value: string) => void;
}) {
  return (
    <header className="sticky top-[65px] z-20 border-b border-border bg-background md:top-0">
      <div className="flex flex-col gap-4 px-4 py-4 md:px-6">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
          <div className="space-y-2">
            <div className="text-[10px] leading-4 tracking-[0.1em] text-muted-foreground uppercase">
              SwarmMind / {VIEW_LABELS[activeView]}
            </div>
            <div className="space-y-1">
              <h1 className="font-heading text-[28px] leading-9 font-semibold tracking-[-0.02em] text-foreground">
                {VIEW_LABELS[activeView]}
              </h1>
              <p className="max-w-2xl text-[13px] leading-5 text-muted-foreground">
                {viewDescriptions[activeView]}
              </p>
            </div>
          </div>

          <div className="flex flex-col gap-3 lg:min-w-[420px]">
            <div className="relative w-full xl:max-w-[400px]">
              <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                value={searchQuery}
                onChange={(e) => { onSearchQueryChange(e.target.value); }}
                placeholder="搜索会话记录..."
                className="pl-9"
              />
            </div>
            <div className="flex flex-wrap gap-2 pt-1 xl:justify-end">
              <Button variant="outline" onClick={onSecondaryAction}>
                {viewActions[activeView].secondary}
              </Button>
              <Button onClick={onPrimaryAction}>
                {viewActions[activeView].primary}
              </Button>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}

export default function App() {
  const [activeView, setActiveView] = useState<SidebarView>("workbench");
  const [activeConversationId, setActiveConversationId] = useState<
    string | undefined
  >(undefined);
  const [recentConversations, setRecentConversations] = useState<
    ConversationRecord[]
  >([]);
  const [draftResetToken, setDraftResetToken] = useState(0);
  const [searchQuery, setSearchQuery] = useState("");

  const fetchRecentConversations = useCallback(async () => {
    try {
      const response = await fetch("/conversations");
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = (await response.json()) as { items: ConversationRecord[] };
      setRecentConversations(
        [...data.items].sort((left, right) => {
          const leftTime = new Date(left.updated_at).getTime();
          const rightTime = new Date(right.updated_at).getTime();
          return rightTime - leftTime;
        }),
      );
    } catch (error) {
      console.error("Failed to fetch recent conversations:", error);
    }
  }, []);

  useEffect(() => {
    void fetchRecentConversations();
  }, [fetchRecentConversations]);

  const handleViewChange = (view: SidebarView) => {
    setActiveView(view);
  };

  const handleStartChat = () => {
    setActiveConversationId(undefined);
    setDraftResetToken((current) => current + 1);
    setActiveView("chat");
  };

  const handleSelectConversation = (conversationId: string) => {
    setActiveConversationId(conversationId);
    setActiveView("chat");
  };

  const handleDeleteConversation = useCallback(
    async (conversationId: string) => {
      const response = await fetch(`/conversations/${conversationId}`, {
        method: "DELETE",
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      setRecentConversations((previous) =>
        previous.filter((conversation) => conversation.id !== conversationId),
      );

      if (activeConversationId === conversationId) {
        setActiveConversationId(undefined);
        setDraftResetToken((current) => current + 1);
        setActiveView("chat");
      }
    },
    [activeConversationId],
  );

  const handlePrimaryAction = () => {
    if (activeView === "chat") {
      handleStartChat();
      return;
    }

    if (activeView === "workbench" || activeView === "projects") {
      handleViewChange("projects");
      return;
    }

    if (activeView === "recent") {
      handleViewChange("chat");
    }
  };

  const handleSecondaryAction = () => {
    if (activeView === "workbench" || activeView === "chat") {
      handleViewChange("recent");
    }
  };

  const filteredConversations = useMemo(() => {
    if (!searchQuery.trim()) return recentConversations;
    const q = searchQuery.trim().toLowerCase();
    return recentConversations.filter((c) =>
      c.title.toLowerCase().includes(q)
    );
  }, [recentConversations, searchQuery]);

  const renderContent = () => {
    switch (activeView) {
      case "workbench":
        return (
          <Workbench
            onStartChat={handleStartChat}
            onOpenProjects={() => { handleViewChange("projects"); }}
            onOpenApprovals={() => { handleViewChange("recent"); }}
          />
        );
      case "chat":
        return (
          <V0Chat
            conversationId={activeConversationId}
            draftResetToken={draftResetToken}
            onConversationCreated={(id) => {
              setActiveConversationId(id);
            }}
            onConversationsChange={setRecentConversations}
          />
        );
      case "teams":
        return (
          <PlaceholderView
            icon={<Bot className="size-5" />}
            title="Agent Team"
            description="为项目挂载可复用 Team，并在这里统一查看配置与治理边界。"
            action="新建 Team"
          />
        );
      case "skills":
        return (
          <PlaceholderView
            icon={<Sparkles className="size-5" />}
            title="技能中心"
            description="统一管理 MCP 与技能绑定，避免能力散落在不同页面里。"
            action="配置能力"
          />
        );
      case "assets":
        return (
          <PlaceholderView
            icon={<Library className="size-5" />}
            title="资源库"
            description="管理报告、摘要、导出文件和可复用模板。"
            action="查看产物"
          />
        );
      case "knowledge":
        return (
          <PlaceholderView
            icon={<BookOpenText className="size-5" />}
            title="知识库"
            description="连接企业知识源，并把引用范围纳入工作流控制。"
            action="连接知识源"
          />
        );
      case "projects":
        return (
          <PlaceholderView
            icon={<FolderKanban className="size-5" />}
            title="项目"
            description="项目空间用于承接结构化执行、审批、结果沉淀与复用。"
            action="新建项目"
          />
        );
      case "recent":
        return (
          <PlaceholderView
            icon={<History className="size-5" />}
            title="最近记录"
            description="快速回到最近的生成任务、项目和输出结果。"
            action="继续任务"
          />
        );
      case "schedules":
        return (
          <PlaceholderView
            icon={<Clock3 className="size-5" />}
            title="定时任务"
            description="配置周期生成、汇总与提醒，使企业任务自动化可交付。"
            action="新建任务"
          />
        );
      default:
        return null;
    }
  };

  return (
    <div
      className={cn(
        "page-shell",
        activeView === "chat" ? "h-[100dvh] overflow-hidden" : "min-h-screen",
      )}
    >
      <Sidebar
        activeView={activeView}
        onViewChange={handleViewChange}
        recentConversations={filteredConversations}
        onSelectConversation={handleSelectConversation}
        onDeleteConversation={handleDeleteConversation}
        pageTitle={VIEW_LABELS[activeView]}
        searchQuery={searchQuery}
      />

      <main
        className={cn(
          "flex flex-col md:ml-[248px]",
          activeView === "chat"
            ? "h-[100dvh] min-h-0 overflow-hidden"
            : "min-h-screen",
        )}
      >
        {activeView !== "chat" && (
          <PageHeader
            activeView={activeView}
            onPrimaryAction={handlePrimaryAction}
            onSecondaryAction={handleSecondaryAction}
            searchQuery={searchQuery}
            onSearchQueryChange={setSearchQuery}
          />
        )}
        <div
          className={
            activeView === "chat"
              ? "flex min-h-0 flex-1 flex-col overflow-hidden pt-[65px] md:pt-0"
              : "flex-1 pt-[65px] md:pt-0"
          }
        >
          {renderContent()}
        </div>
      </main>
    </div>
  );
}
