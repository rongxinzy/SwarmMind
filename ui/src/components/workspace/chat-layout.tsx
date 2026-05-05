"use client";

import type { ReactNode } from "react";
import { Download, FilesIcon, GitBranch, XIcon } from "lucide-react";

import { Button } from "@/components/ui/button";
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
    <div className="flex h-full w-full">
      <div
        className={cn(
          "relative flex h-full flex-col transition-all duration-300",
          artifactsOpen ? "w-[60%]" : "w-full",
        )}
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
      </div>

      {artifactsOpen && <div className="w-px cursor-col-resize bg-border hover:bg-border/80" />}

      {artifactsOpen && (
        <div className="flex h-full w-[40%] min-w-[300px] max-w-[600px] flex-col border-l bg-background">
          <div className="flex items-center justify-between border-b px-4 py-3">
            {/* Tab switcher */}
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
                <div className="flex h-full flex-col">
                  <div className="flex items-center justify-between border-b bg-muted/50 px-4 py-2">
                    <span className="max-w-[200px] truncate text-sm font-medium">{selectedArtifact.split("/").pop()}</span>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => { onSelectArtifact(null); }}
                    >
                      返回列表
                    </Button>
                  </div>
                  <div className="flex-1 overflow-auto p-4">
                    <iframe
                      src={`/api/conversations/${conversationId}/artifacts${selectedArtifact}`}
                      className="h-full w-full rounded-lg border"
                      title={selectedArtifact}
                    />
                  </div>
                </div>
              ) : (
                <div className="p-4">
                  <ArtifactFileListSimple files={artifacts} onSelect={onSelectArtifact} />
                </div>
              )
            ) : null}
          </div>
        </div>
      )}
    </div>
  );
}

function ArtifactFileListSimple({
  files,
  onSelect,
}: {
  files: string[];
  onSelect: (path: string) => void;
}) {
  return (
    <div className="flex flex-col gap-2">
      {files.map((file) => (
        <button
          key={file}
          onClick={() => { onSelect(file); }}
          className="flex items-center gap-3 rounded-lg border p-3 text-left transition-colors hover:bg-muted"
        >
          <FilesIcon className="size-5 text-muted-foreground" />
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium">{file.split("/").pop()}</p>
            <p className="truncate text-xs text-muted-foreground">{file}</p>
          </div>
        </button>
      ))}
    </div>
  );
}
