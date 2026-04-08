"use client";

import { Collapsible } from "@/components/ui/collapsible";
import { cn } from "@/lib/utils";
import {
  BookOpenTextIcon,
  FolderOpenIcon,
  GlobeIcon,
  LightbulbIcon,
  ListTodoIcon,
  MessageCircleQuestionMarkIcon,
  NotebookPenIcon,
  SearchIcon,
  SquareTerminalIcon,
  WrenchIcon,
  type LucideIcon,
} from "lucide-react";
import type { ComponentProps, ReactNode } from "react";
import { createContext, useState } from "react";

// ============================================================================
// ChainOfThought Context
// ============================================================================

interface ChainOfThoughtContextValue {
  open: boolean;
  setOpen: (open: boolean) => void;
}

const ChainOfThoughtContext = createContext<ChainOfThoughtContextValue | null>(null);

// ============================================================================
// ChainOfThought Root
// ============================================================================

export type ChainOfThoughtProps = Omit<ComponentProps<typeof Collapsible>, "open" | "onOpenChange"> & {
  open?: boolean;
  defaultOpen?: boolean;
  onOpenChange?: (open: boolean) => void;
};

export const ChainOfThought = ({
  className,
  children,
  open: openProp,
  defaultOpen = false,
  onOpenChange,
  ...props
}: ChainOfThoughtProps) => {
  const [open, setOpen] = useState(defaultOpen);

  const isOpen = openProp !== undefined ? openProp : open;
  const handleOpenChange = (newOpen: boolean) => {
    if (openProp === undefined) {
      setOpen(newOpen);
    }
    onOpenChange?.(newOpen);
  };

  return (
    <ChainOfThoughtContext.Provider value={{ open: isOpen, setOpen: handleOpenChange }}>
      <Collapsible
        className={cn("flex flex-col", className)}
        open={isOpen}
        onOpenChange={handleOpenChange}
        {...props}
      >
        {children}
      </Collapsible>
    </ChainOfThoughtContext.Provider>
  );
};

// ============================================================================
// ChainOfThoughtContent
// ============================================================================

export type ChainOfThoughtContentProps = ComponentProps<"div">;

export const ChainOfThoughtContent = ({ className, children, ...props }: ChainOfThoughtContentProps) => (
  <div className={cn("flex flex-col gap-3", className)} {...props}>
    {children}
  </div>
);

// ============================================================================
// ChainOfThoughtStep
// ============================================================================

export type ChainOfThoughtStepProps = ComponentProps<"div"> & {
  label: ReactNode;
  icon?: LucideIcon | ReactNode;
};

export const ChainOfThoughtStep = ({
  className,
  children,
  label,
  icon: Icon,
  ...props
}: ChainOfThoughtStepProps) => (
  <div className={cn("flex items-start gap-3 text-sm", className)} {...props}>
    {Icon && (
      <div className="mt-0.5 shrink-0 text-muted-foreground">
        {typeof Icon === "function" ? <Icon className="size-4" /> : Icon}
      </div>
    )}
    <div className="flex-1 min-w-0">
      <div className="font-medium text-foreground">{label}</div>
      {children && <div className="mt-1">{children}</div>}
    </div>
  </div>
);

// ============================================================================
// ChainOfThoughtSearchResults
// ============================================================================

export type ChainOfThoughtSearchResultsProps = ComponentProps<"div">;

export const ChainOfThoughtSearchResults = ({ className, children, ...props }: ChainOfThoughtSearchResultsProps) => (
  <div className={cn("mt-3 flex flex-wrap gap-2", className)} {...props}>
    {children}
  </div>
);

// ============================================================================
// ChainOfThoughtSearchResult
// ============================================================================

export type ChainOfThoughtSearchResultProps = ComponentProps<"a">;

export const ChainOfThoughtSearchResult = ({
  className,
  children,
  href,
  ...props
}: ChainOfThoughtSearchResultProps) => (
  <a
    className={cn(
      "inline-flex items-center gap-1.5 rounded-md bg-secondary px-2.5 py-1.5 text-xs font-medium text-foreground hover:bg-secondary/80 transition-colors",
      className
    )}
    href={href}
    target="_blank"
    rel="noreferrer"
    {...props}
  >
    {children}
  </a>
);

// ============================================================================
// Tool Call Visualizations
// ============================================================================

export type ToolCallType = 
  | "web_search"
  | "image_search"
  | "web_fetch"
  | "ls"
  | "read_file"
  | "write_file"
  | "str_replace"
  | "bash"
  | "ask_clarification"
  | "write_todos"
  | string;

export const TOOL_ICONS: Record<string, LucideIcon> = {
  web_search: SearchIcon,
  image_search: SearchIcon,
  web_fetch: GlobeIcon,
  ls: FolderOpenIcon,
  read_file: BookOpenTextIcon,
  write_file: NotebookPenIcon,
  str_replace: NotebookPenIcon,
  bash: SquareTerminalIcon,
  ask_clarification: MessageCircleQuestionMarkIcon,
  write_todos: ListTodoIcon,
};

export const TOOL_LABELS: Record<string, string> = {
  web_search: "搜索相关信息",
  image_search: "搜索相关图片",
  web_fetch: "获取网页内容",
  ls: "列出文件夹",
  read_file: "读取文件",
  write_file: "写入文件",
  str_replace: "替换文件内容",
  bash: "执行命令",
  ask_clarification: "需要您的帮助",
  write_todos: "创建任务列表",
};

export interface ToolCallData {
  id: string;
  name: string;
  args: Record<string, unknown>;
  result?: unknown;
}

export interface ToolCallStepProps {
  toolCall: ToolCallData;
  isLoading?: boolean;
  className?: string;
}

export const ToolCallStep = ({ toolCall, isLoading, className }: ToolCallStepProps) => {
  const { name, args } = toolCall;
  const Icon = TOOL_ICONS[name] || WrenchIcon;
  const defaultLabel = TOOL_LABELS[name] || `使用工具: ${name}`;
  
  // Get description from args or use default
  const description = (args.description as string) || defaultLabel;
  
  // Get additional details based on tool type
  const getDetail = () => {
    switch (name) {
      case "web_search":
        return args.query as string;
      case "web_fetch":
        return args.url as string;
      case "read_file":
      case "write_file":
      case "str_replace":
        return args.path as string;
      case "bash":
        return args.command as string;
      default:
        return undefined;
    }
  };

  const detail = getDetail();

  return (
    <ChainOfThoughtStep
      className={cn("rounded-lg border bg-card p-3", className)}
      label={
        <div className="flex items-center gap-2">
          <span>{description}</span>
          {isLoading && (
            <span className="inline-block size-2 animate-pulse rounded-full bg-primary" />
          )}
        </div>
      }
      icon={Icon}
    >
      {detail && (
        <ChainOfThoughtSearchResult className="mt-2">
          {detail}
        </ChainOfThoughtSearchResult>
      )}
    </ChainOfThoughtStep>
  );
};

// ============================================================================
// ReasoningStep
// ============================================================================

export interface ReasoningStepProps {
  content: string;
  className?: string;
}

export const ReasoningStep = ({ content, className }: ReasoningStepProps) => (
  <ChainOfThoughtStep
    className={cn("rounded-lg border border-dashed bg-secondary/50 p-3", className)}
    label="思考过程"
    icon={LightbulbIcon}
  >
    <div className="mt-2 whitespace-pre-wrap text-sm text-muted-foreground leading-relaxed">
      {content}
    </div>
  </ChainOfThoughtStep>
);
