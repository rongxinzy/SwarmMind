"use client";

import type { ReactNode } from "react";
import { Download, FilesIcon, XIcon } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface ChatLayoutProps {
  children: ReactNode;
  conversationId?: string;
  artifacts: string[];
  selectedArtifact: string | null;
  onSelectArtifact: (path: string | null) => void;
  artifactsOpen: boolean;
  setArtifactsOpen: (open: boolean) => void;
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
  onExport,
}: ChatLayoutProps) {
  return (
    <div className="flex h-full w-full">
      <div
        className={cn(
          "relative flex h-full flex-col transition-all duration-300",
          artifactsOpen ? "w-[60%]" : "w-full",
        )}
      >
        {(artifacts.length > 0 || onExport) && !artifactsOpen && (
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
            {artifacts.length > 0 && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
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
            <h3 className="text-sm font-medium">Artifacts</h3>
            <div className="flex items-center gap-2">
              {artifacts.length > 0 && <span className="text-xs text-muted-foreground">{artifacts.length} 个文件</span>}
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
          </div>

          <div className="flex-1 overflow-hidden">
            {artifacts.length === 0 ? (
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
                    onClick={() => {
                      onSelectArtifact(null);
                    }}
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
            )}
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
          onClick={() => {
            onSelect(file);
          }}
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
