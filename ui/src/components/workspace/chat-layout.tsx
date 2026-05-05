"use client";

import type { ReactNode } from "react";
import { Download, FilesIcon, GitBranch, XIcon } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from "@/components/ui/resizable";
import {
  ArtifactFileDetail,
  ArtifactFileList,
} from "@/components/workspace/artifacts/artifact-file-list";
import { TracePanel } from "@/components/workspace/trace-panel";
import { cn } from "@/lib/utils";

type RightPanelTab = "artifacts" | "trace";

interface ChatLayoutProps {
  children: ReactNode;
  conversationId?: string;
  artifacts: string[];
  selectedArtifact: string | null;
  onSelectArtifact: (path: string | null) => void;
  artifactsOpen: boolean;
  setArtifactsOpen: (open: boolean) => void;
  rightPanelTab?: RightPanelTab;
  setRightPanelTab?: (tab: RightPanelTab) => void;
  onExport?: (format: "markdown" | "json") => void;
}

export function ChatLayout({
  children,
  conversationId,
  artifacts,
  selectedArtifact,
  onSelectArtifact,
  artifactsOpen,
  setArtifactsOpen,
  rightPanelTab = "artifacts",
  setRightPanelTab,
  onExport,
}: ChatLayoutProps) {
  const showHeaderButtons = (artifacts.length > 0 || onExport || conversationId) && !artifactsOpen;

  return (
    <ResizablePanelGroup
      id="swarmmind-chat-panels"
      orientation="horizontal"
      defaultLayout={artifactsOpen ? { chat: 62, side: 38 } : { chat: 100 }}
      className="h-full w-full"
    >
      <ResizablePanel
        id="chat"
        defaultSize={artifactsOpen ? "62%" : "100%"}
        minSize="42%"
        className="relative flex h-full min-h-0 flex-col"
      >
        {showHeaderButtons && (
          <div className="absolute right-3 top-3 z-10 flex items-center gap-2">
            {onExport ? (
              <Button
                variant="outline"
                size="sm"
                onClick={() => { onExport("markdown"); }}
                className="gap-1.5 text-xs"
                title="导出会话为 Markdown"
              >
                <Download className="size-3.5" />
                导出
              </Button>
            ) : null}
            {conversationId ? (
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setRightPanelTab?.("trace");
                  setArtifactsOpen(true);
                }}
                className="gap-1.5 text-xs"
                title="查看 Agent 执行轨迹"
              >
                <GitBranch className="size-3.5" />
                轨迹
              </Button>
            ) : null}
            {artifacts.length > 0 && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setRightPanelTab?.("artifacts");
                  setArtifactsOpen(true);
                }}
                className="gap-1.5 text-xs"
              >
                <FilesIcon className="size-3.5" />
                {artifacts.length} 个产物
              </Button>
            )}
          </div>
        )}
        {children}
      </ResizablePanel>

      {artifactsOpen ? (
        <ResizableHandle
          id="swarmmind-chat-side-resizer"
          withHandle
          className="opacity-60 transition-opacity hover:opacity-100"
        />
      ) : null}

      {artifactsOpen ? (
        <ResizablePanel
          id="side"
          defaultSize="38%"
          minSize="28%"
          maxSize="56%"
          className="min-w-[300px]"
        >
        <div className="flex h-full min-h-0 flex-col border-l bg-background">
          <div className="flex items-center justify-between border-b px-4 py-3">
            <div className="flex items-center gap-1">
              <button
                onClick={() => { setRightPanelTab?.("artifacts"); }}
                className={cn(
                  "flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-medium transition-colors",
                  rightPanelTab === "artifacts"
                    ? "bg-muted text-foreground"
                    : "text-muted-foreground hover:text-foreground",
                )}
              >
                <FilesIcon className="size-3.5" />
                产物
                {artifacts.length > 0 && (
                  <span className="rounded-full bg-muted-foreground/20 px-1.5 py-0.5 text-[10px]">
                    {artifacts.length}
                  </span>
                )}
              </button>
              {conversationId && (
                <button
                  onClick={() => { setRightPanelTab?.("trace"); }}
                  className={cn(
                    "flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-medium transition-colors",
                    rightPanelTab === "trace"
                      ? "bg-muted text-foreground"
                      : "text-muted-foreground hover:text-foreground",
                  )}
                >
                  <GitBranch className="size-3.5" />
                  执行轨迹
                </button>
              )}
            </div>

            <Button
              variant="ghost"
              size="icon-sm"
              onClick={() => {
                setArtifactsOpen(false);
              }}
            >
              <XIcon className="size-4" />
            </Button>
          </div>

          <div className="flex-1 overflow-hidden">
            {rightPanelTab === "trace" && conversationId ? (
              <TracePanel conversationId={conversationId} />
            ) : rightPanelTab === "artifacts" || !conversationId ? (
              artifacts.length === 0 ? (
                <div className="flex h-full flex-col items-center justify-center p-8 text-center">
                  <FilesIcon className="mb-4 size-12 text-muted-foreground/50" />
                  <h4 className="mb-2 text-sm font-medium">没有 Artifacts</h4>
                  <p className="max-w-[200px] text-xs text-muted-foreground">当 AI 生成文件时，它们将显示在这里</p>
                </div>
              ) : selectedArtifact ? (
                <div className="flex h-full min-h-0 flex-col">
                  <ArtifactFileDetail
                    filepath={selectedArtifact}
                    conversationId={conversationId}
                    onBack={() => { onSelectArtifact(null); }}
                    className="min-h-0 flex-1"
                  />
                </div>
              ) : (
                <div className="h-full overflow-auto p-4">
                  <ArtifactFileList
                    files={artifacts}
                    selectedPath={selectedArtifact}
                    onSelectPath={onSelectArtifact}
                    conversationId={conversationId}
                  />
                </div>
              )
            ) : null}
          </div>
        </div>
        </ResizablePanel>
      ) : null}
    </ResizablePanelGroup>
  );
}
