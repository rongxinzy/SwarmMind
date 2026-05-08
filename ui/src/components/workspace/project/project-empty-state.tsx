import { FolderKanban } from "lucide-react";

export function ProjectEmptyState() {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-4 p-12 text-center">
      <div className="flex size-14 items-center justify-center rounded-2xl border border-border bg-surface-hover">
        <FolderKanban className="size-6 text-muted-foreground" />
      </div>
      <div className="space-y-1">
        <h3 className="text-sm font-semibold text-foreground">未选择项目</h3>
        <p className="max-w-xs text-xs text-muted-foreground">
          从对话工作区点击「升级为项目」，或在此处新建项目。
        </p>
      </div>
    </div>
  );
}
