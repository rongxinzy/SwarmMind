"use client";

import { DownloadIcon, FileIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { useArtifacts } from "./context";
import { resolveArtifactURL } from "@/core/artifacts/utils";
import { getFileName, getFileExtensionDisplayName, getFileIcon } from "@/core/utils/files";

// ============================================================================
// ArtifactFileList Component
// ============================================================================

interface ArtifactFileListProps {
  className?: string;
  files: string[];
  conversationId?: string;
  selectedPath?: string | null;
  onSelectPath?: (path: string) => void;
}

export function ArtifactFileList({
  className,
  files,
  conversationId,
  selectedPath,
  onSelectPath,
}: ArtifactFileListProps) {
  const { selectArtifact, selectedArtifact } = useArtifacts();

  const handleClick = (filepath: string) => {
    onSelectPath?.(filepath);
    const artifact = {
      id: filepath,
      path: filepath,
      filename: getFileName(filepath),
    };
    selectArtifact(artifact);
  };

  return (
    <ul className={cn("flex w-full flex-col gap-3", className)}>
      {files.map((file) => (
        <ArtifactFileCard
          key={file}
          filepath={file}
          isSelected={selectedPath === file || selectedArtifact?.path === file}
          onClick={() => { handleClick(file); }}
          conversationId={conversationId}
        />
      ))}
    </ul>
  );
}

// ============================================================================
// ArtifactFileCard Component
// ============================================================================

interface ArtifactFileCardProps {
  filepath: string;
  isSelected?: boolean;
  onClick: () => void;
  conversationId?: string;
}

function ArtifactFileCard({
  filepath,
  isSelected,
  onClick,
  conversationId,
}: ArtifactFileCardProps) {
  const filename = getFileName(filepath);
  const fileIcon = getFileIcon(filepath);
  const artifactURL = conversationId ? resolveArtifactURL(filepath, conversationId) : undefined;

  return (
    <Card
      className={cn(
        "relative cursor-pointer p-3 transition-colors",
        isSelected && "border-primary bg-primary/5"
      )}
      onClick={onClick}
    >
      <CardHeader className="pr-2 pl-1">
        <CardTitle className="relative pl-8 text-sm">
          <div className="truncate">{filename}</div>
          <div className="absolute top-0 left-0 text-muted-foreground">
            {fileIcon}
          </div>
        </CardTitle>
        <CardDescription className="pl-8 text-xs">
          {getFileExtensionDisplayName(filepath)} file
        </CardDescription>
        <div className="absolute top-2 right-2 flex gap-1">
          {artifactURL ? (
            <a
              href={artifactURL}
              target="_blank"
              rel="noopener noreferrer"
              onClick={(e) => { e.stopPropagation(); }}
            >
              <Button variant="ghost" size="icon-sm">
                <DownloadIcon className="size-4" />
              </Button>
            </a>
          ) : null}
        </div>
      </CardHeader>
    </Card>
  );
}

// ============================================================================
// ArtifactFileDetail Component (Simplified)
// ============================================================================

interface ArtifactFileDetailProps {
  className?: string;
  filepath?: string;
  conversationId?: string;
  onBack?: () => void;
}

export function ArtifactFileDetail({
  className,
  filepath,
  conversationId,
  onBack,
}: ArtifactFileDetailProps) {
  const { selectedArtifact, setOpen } = useArtifacts();

  const artifact = selectedArtifact;
  if (!artifact && !filepath) {
    return (
      <div className={cn("flex h-full items-center justify-center", className)}>
        <p className="text-muted-foreground text-sm">选择文件查看详情</p>
      </div>
    );
  }

  const displayPath = filepath ?? artifact?.path ?? "";
  const filename = getFileName(displayPath);
  const artifactURL = conversationId && displayPath ? resolveArtifactURL(displayPath, conversationId) : undefined;

  return (
    <div className={cn("flex h-full flex-col", className)}>
      <div className="flex items-center justify-between border-b p-3">
        <div className="flex items-center gap-2">
          <FileIcon className="size-4" />
          <span className="font-medium text-sm truncate max-w-[200px]">
            {filename}
          </span>
        </div>
        <div className="flex gap-1">
          {onBack ? (
            <Button variant="ghost" size="sm" onClick={onBack}>
              返回列表
            </Button>
          ) : null}
          {artifactURL ? (
            <a
              href={artifactURL}
              target="_blank"
              rel="noopener noreferrer"
            >
              <Button variant="ghost" size="icon-sm">
                <DownloadIcon className="size-4" />
              </Button>
            </a>
          ) : null}
          <Button variant="ghost" size="icon-sm" onClick={() => { setOpen(false); }}>
            ✕
          </Button>
        </div>
      </div>
      <div className="flex-1 p-4 overflow-auto">
        {artifactURL ? (
          <iframe
            src={artifactURL}
            className="w-full h-full border-0"
            title={filename}
          />
        ) : null}
      </div>
    </div>
  );
}
