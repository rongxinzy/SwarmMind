"use client"

import type { Message } from "@langchain/langgraph-sdk"
import {
  BookOpenTextIcon,
  ChevronUpIcon,
  FolderOpenIcon,
  GlobeIcon,
  LightbulbIcon,
  ListTodoIcon,
  MessageCircleQuestionMarkIcon,
  NotebookPenIcon,
  SearchIcon,
  SquareTerminalIcon,
  WrenchIcon,
} from "lucide-react"
import { useMemo, useState } from "react"

import {
  ChainOfThought,
  ChainOfThoughtContent,
  ChainOfThoughtSearchResult,
  ChainOfThoughtSearchResults,
  ChainOfThoughtStep,
} from "@/components/ai-elements/chain-of-thought"
import { CodeBlock } from "@/components/ai-elements/code-block"
import { Button } from "@/components/ui/button"
import {
  createWriteFileArtifactReference,
  normalizeArtifactPath,
} from "@/core/deerflow/artifacts"
import {
  extractReasoningContentFromMessage,
  findToolCallResult,
} from "@/core/deerflow/messages"
import { extractTitleFromMarkdown } from "@/core/deerflow/markdown"
import { normalizePlanSteps } from "@/core/deerflow/todos"
import { cn } from "@/lib/utils"
import type { ChatPlanStep, ChatPlanStepStatus } from "@/types/chat"

import { FlipDisplay } from "./FlipDisplay"
import { MarkdownContent } from "./MarkdownContent"

type CoTStep = CoTReasoningStep | CoTToolCallStep

interface GenericCoTStep<T extends string = string> {
  id?: string
  messageId?: string
  type: T
}

interface CoTReasoningStep extends GenericCoTStep<"reasoning"> {
  reasoning: string | null
}

interface CoTToolCallStep extends GenericCoTStep<"toolCall"> {
  name: string
  args: Record<string, unknown>
  result?: string | Record<string, unknown> | unknown[]
}

export function ProcessingGroup({
  className,
  conversationId,
  isLoading = false,
  messages,
  onArtifactSelect,
}: {
  className?: string
  conversationId?: string
  isLoading?: boolean
  messages: Message[]
  onArtifactSelect?: (file: string) => void
}) {
  const [showAbove, setShowAbove] = useState(false)
  const [showLastThinking, setShowLastThinking] = useState(false)
  const steps = useMemo(() => convertToSteps(messages), [messages])
  const lastToolCallStep = useMemo(() => {
    const toolSteps = steps.filter((step): step is CoTToolCallStep => step.type === "toolCall")
    return toolSteps[toolSteps.length - 1]
  }, [steps])
  const aboveLastToolCallSteps = useMemo(() => {
    if (!lastToolCallStep) {
      return []
    }
    const index = steps.indexOf(lastToolCallStep)
    return steps.slice(0, index)
  }, [lastToolCallStep, steps])
  const lastReasoningStep = useMemo(() => {
    if (lastToolCallStep) {
      const index = steps.indexOf(lastToolCallStep)
      return steps.slice(index + 1).find((step): step is CoTReasoningStep => step.type === "reasoning")
    }
    const reasoningSteps = steps.filter((step): step is CoTReasoningStep => step.type === "reasoning")
    return reasoningSteps[reasoningSteps.length - 1]
  }, [lastToolCallStep, steps])

  if (steps.length === 0) {
    return null
  }

  const isActive = isLoading && (Boolean(lastToolCallStep) || Boolean(lastReasoningStep))

  return (
    <ChainOfThought
      className={cn(
        "relative w-full gap-2 overflow-hidden rounded-xl border border-[#e7e7e4] bg-white p-1 shadow-[0_10px_30px_rgba(20,20,20,0.035)]",
        isActive && "border-[#ded8ff]",
        className,
      )}
      open
    >
      {isActive && (
        <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-[#7256f4] via-[#a978ff] to-[#ff80b5]" />
      )}
      {aboveLastToolCallSteps.length > 0 && (
        <Button
          className="w-full items-start justify-start rounded-lg text-left text-[#5f5f5f] hover:bg-[#f7f7f5] hover:text-[#1f1f1f]"
          variant="ghost"
          onClick={() => setShowAbove((current) => !current)}
        >
          <ChainOfThoughtStep
            label={
              <span className="opacity-60">
                {showAbove ? "收起早前步骤" : `展开 ${aboveLastToolCallSteps.length} 个早前步骤`}
              </span>
            }
            icon={ChevronUpIcon}
          />
        </Button>
      )}
      {lastToolCallStep && (
        <ChainOfThoughtContent className="px-2 pb-2 pt-1 sm:px-3">
          {showAbove &&
            aboveLastToolCallSteps.map((step) =>
              step.type === "reasoning" ? (
                <ReasoningStep
                  key={step.id ?? step.reasoning ?? "reasoning"}
                  conversationId={conversationId}
                  step={step}
                  isLoading={isLoading}
                  onArtifactSelect={onArtifactSelect}
                />
              ) : (
                <ToolCall
                  key={step.id ?? step.name}
                  {...step}
                  isLoading={isLoading}
                  onArtifactSelect={onArtifactSelect}
                />
              ),
            )}
          <FlipDisplay uniqueKey={lastToolCallStep.id ?? lastToolCallStep.name}>
            <ToolCall
              key={lastToolCallStep.id ?? lastToolCallStep.name}
              {...lastToolCallStep}
              isLast
              isLoading={isLoading}
              onArtifactSelect={onArtifactSelect}
            />
          </FlipDisplay>
        </ChainOfThoughtContent>
      )}
      {lastReasoningStep && (
        <>
          <Button
            className="w-full items-start justify-start rounded-lg text-left text-[#3d3d3d] hover:bg-[#f7f7f5]"
            variant="ghost"
            onClick={() => setShowLastThinking((current) => !current)}
          >
            <div className="flex w-full items-center justify-between">
              <ChainOfThoughtStep className="font-normal" label="思考中" icon={LightbulbIcon} />
              <ChevronUpIcon className={cn("size-4 text-muted-foreground", showLastThinking ? "" : "rotate-180")} />
            </div>
          </Button>
          {showLastThinking && (
            <ChainOfThoughtContent className="px-2 pb-2 sm:px-3">
              <ReasoningStep
                conversationId={conversationId}
                step={lastReasoningStep}
                isLoading={isLoading}
                onArtifactSelect={onArtifactSelect}
              />
            </ChainOfThoughtContent>
          )}
        </>
      )}
    </ChainOfThought>
  )
}

function ReasoningStep({
  conversationId,
  step,
  isLoading,
  onArtifactSelect,
}: {
  conversationId?: string
  step: CoTReasoningStep
  isLoading: boolean
  onArtifactSelect?: (file: string) => void
}) {
  return (
    <ChainOfThoughtStep
      className="rounded-lg bg-[#fbfbfa] px-2.5 py-2 text-[#4b4b4b]"
      label={
        <MarkdownContent
          conversationId={conversationId}
          content={step.reasoning ?? ""}
          isLoading={isLoading}
          onArtifactSelect={onArtifactSelect}
        />
      }
    />
  )
}

function ToolCall({
  id,
  messageId,
  name,
  args,
  result,
  isLast = false,
  isLoading = false,
  onArtifactSelect,
}: CoTToolCallStep & {
  isLast?: boolean
  isLoading?: boolean
  onArtifactSelect?: (file: string) => void
}) {
  const toolStepClassName = cn(
    "rounded-lg px-2.5 py-2 transition-colors",
    isLast && isLoading
      ? "bg-[#fbfbff] text-[#1f1f1f] shadow-[inset_2px_0_0_#7256f4]"
      : "text-[#444] hover:bg-[#fafaf8]",
  )

  if (name === "web_search") {
    const query = typeof args.query === "string" ? args.query : undefined
    return (
      <ChainOfThoughtStep
        key={id}
        className={toolStepClassName}
        label={query ? `搜索网页: ${query}` : "搜索相关信息"}
        icon={SearchIcon}
        status={isLast && isLoading ? "active" : "complete"}
      >
        <SearchResults result={result} />
      </ChainOfThoughtStep>
    )
  }

  if (name === "image_search") {
    const query = typeof args.query === "string" ? args.query : undefined
    return (
      <ChainOfThoughtStep
        key={id}
        className={toolStepClassName}
        label={query ? `搜索图片: ${query}` : "搜索相关图片"}
        icon={SearchIcon}
        status={isLast && isLoading ? "active" : "complete"}
      >
        <ImageSearchResults result={result} />
      </ChainOfThoughtStep>
    )
  }

  if (name === "web_fetch") {
    const url = typeof args.url === "string" ? args.url : undefined
    const title =
      typeof result === "string"
        ? extractTitleFromMarkdown(result) ?? url
        : url
    return (
      <ChainOfThoughtStep
        key={id}
        className={toolStepClassName}
        label="查看网页"
        icon={GlobeIcon}
        status={isLast && isLoading ? "active" : "complete"}
      >
        {url && (
          <ChainOfThoughtSearchResult>
            <a href={url} target="_blank" rel="noopener noreferrer">
              {title}
            </a>
          </ChainOfThoughtSearchResult>
        )}
      </ChainOfThoughtStep>
    )
  }

  if (name === "ls") {
    const description = typeof args.description === "string" ? args.description : "列出目录"
    const path = typeof args.path === "string" ? args.path : undefined
    return (
      <ChainOfThoughtStep
        key={id}
        className={toolStepClassName}
        label={description}
        icon={FolderOpenIcon}
        status={isLast && isLoading ? "active" : "complete"}
      >
        {path && <ChainOfThoughtSearchResult>{path}</ChainOfThoughtSearchResult>}
      </ChainOfThoughtStep>
    )
  }

  if (name === "read_file") {
    const description = typeof args.description === "string" ? args.description : "读取文件"
    const path = typeof args.path === "string" ? args.path : undefined
    return (
      <ChainOfThoughtStep
        key={id}
        className={toolStepClassName}
        label={description}
        icon={BookOpenTextIcon}
        status={isLast && isLoading ? "active" : "complete"}
      >
        {path && <ChainOfThoughtSearchResult>{path}</ChainOfThoughtSearchResult>}
      </ChainOfThoughtStep>
    )
  }

  if (name === "write_file" || name === "str_replace") {
    const description = typeof args.description === "string" ? args.description : "写入文件"
    const path = typeof args.path === "string" ? normalizeArtifactPath(args.path) : null
    const artifactReference =
      name === "write_file" && path
        ? createWriteFileArtifactReference({
            messageId,
            path,
            toolCallId: id,
          }) ?? path
        : path
    const interactive = Boolean(artifactReference && onArtifactSelect)
    return (
      <ChainOfThoughtStep
        key={id}
        className={cn(toolStepClassName, interactive && "cursor-pointer hover:text-foreground")}
        label={description}
        icon={NotebookPenIcon}
        status={isLast && isLoading ? "active" : "complete"}
        data-message-id={messageId}
        data-tool-call-id={id}
        role={interactive ? "button" : undefined}
        tabIndex={interactive ? 0 : undefined}
        onClick={() => {
          if (artifactReference) {
            onArtifactSelect?.(artifactReference)
          }
        }}
        onKeyDown={(event) => {
          if (!artifactReference || !interactive) {
            return
          }
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault()
            onArtifactSelect?.(artifactReference)
          }
        }}
      >
        {path && (
          <ChainOfThoughtSearchResult className={cn(interactive && "cursor-pointer")}>
            {path}
          </ChainOfThoughtSearchResult>
        )}
      </ChainOfThoughtStep>
    )
  }

  if (name === "bash") {
    const description = typeof args.description === "string" ? args.description : "执行命令"
    const command = typeof args.command === "string" ? args.command : undefined
    return (
      <ChainOfThoughtStep
        key={id}
        className={toolStepClassName}
        label={description}
        icon={SquareTerminalIcon}
        status={isLast && isLoading ? "active" : "complete"}
      >
        {command && (
          <CodeBlock
            className="mx-0 cursor-default border-none px-0"
            showLineNumbers={false}
            language="bash"
            code={command}
          />
        )}
      </ChainOfThoughtStep>
    )
  }

  if (name === "ask_clarification") {
    return (
      <ChainOfThoughtStep
        key={id}
        className={toolStepClassName}
        label="需要你的补充"
        icon={MessageCircleQuestionMarkIcon}
        status={isLast && isLoading ? "active" : "complete"}
      />
    )
  }

  if (name === "write_todos") {
    const todos = normalizePlanSteps(args.todos)
    return (
      <ChainOfThoughtStep
        key={id}
        className={toolStepClassName}
        label="更新待办"
        icon={ListTodoIcon}
        status={isLast && isLoading ? "active" : "complete"}
      >
        {todos.length > 0 && <TodoPreview todos={todos} />}
      </ChainOfThoughtStep>
    )
  }

  const description = typeof args.description === "string" ? args.description : `使用工具: ${name}`
  return (
    <ChainOfThoughtStep
      key={id}
      className={toolStepClassName}
      label={description}
      icon={WrenchIcon}
      status={isLast && isLoading ? "active" : "complete"}
      data-loading={isLoading && isLast ? "true" : undefined}
    />
  )
}

function SearchResults({ result }: { result: CoTToolCallStep["result"] }) {
  const items = Array.isArray(result)
    ? result
    : isRecord(result) && Array.isArray(result.results)
      ? result.results
      : []

  if (items.length === 0) {
    return null
  }

  return (
    <ChainOfThoughtSearchResults>
      {items.map((item, index) => {
        if (!isRecord(item)) {
          return null
        }
        const url = typeof item.url === "string" ? item.url : undefined
        const title = typeof item.title === "string" ? item.title : url
        if (!url || !title) {
          return null
        }
        return (
          <ChainOfThoughtSearchResult key={`${url}-${index}`}>
            <a href={url} target="_blank" rel="noopener noreferrer">
              {title}
            </a>
          </ChainOfThoughtSearchResult>
        )
      })}
    </ChainOfThoughtSearchResults>
  )
}

function ImageSearchResults({ result }: { result: CoTToolCallStep["result"] }) {
  const items = isRecord(result) && Array.isArray(result.results) ? result.results : []
  if (items.length === 0) {
    return null
  }

  return (
    <ChainOfThoughtSearchResults>
      {items.map((item, index) => {
        if (!isRecord(item)) {
          return null
        }
        const sourceUrl = typeof item.source_url === "string" ? item.source_url : undefined
        const thumbnailUrl = typeof item.thumbnail_url === "string" ? item.thumbnail_url : undefined
        const title = typeof item.title === "string" ? item.title : "image"
        if (!sourceUrl || !thumbnailUrl) {
          return null
        }
        return (
          <a
            key={`${sourceUrl}-${index}`}
            className="size-24 overflow-hidden rounded-lg border bg-accent"
            href={sourceUrl}
            target="_blank"
            rel="noopener noreferrer"
            title={title}
          >
            <img className="size-full object-cover" src={thumbnailUrl} alt={title} />
          </a>
        )
      })}
    </ChainOfThoughtSearchResults>
  )
}

function TodoPreview({ todos }: { todos: ChatPlanStep[] }) {
  return (
    <div className="mt-2 space-y-1.5 rounded-lg border border-[#eeeeee] bg-[#fbfbfa] p-2">
      {todos.map((todo, index) => (
        <div
          key={`${index}-${todo.content}`}
          className="flex min-w-0 items-start gap-2 text-xs text-[#4f4f4f]"
        >
          <span
            className={cn(
              "mt-1 size-2 shrink-0 rounded-full border",
              todo.status === "completed" && "border-[#2f7d32] bg-[#2f7d32]",
              todo.status === "in_progress" && "border-[#111111] bg-[#111111]",
              todo.status === "pending" && "border-[#cfcfcf] bg-white",
            )}
          />
          <span className={cn("min-w-0 flex-1", todo.status === "completed" && "text-[#8a8a8a] line-through")}>
            {todo.content}
          </span>
          <span className="shrink-0 text-[10px] text-[#8a8a8a]">
            {todoStatusLabel(todo.status)}
          </span>
        </div>
      ))}
    </div>
  )
}

function todoStatusLabel(status: ChatPlanStepStatus) {
  switch (status) {
    case "completed":
      return "完成"
    case "in_progress":
      return "进行中"
    case "pending":
      return "待处理"
  }
}

function convertToSteps(messages: Message[]) {
  const steps: CoTStep[] = []

  for (const message of messages) {
    if (message.type !== "ai") {
      continue
    }

    const reasoning = extractReasoningContentFromMessage(message)
    if (reasoning) {
      steps.push({
        id: message.id,
        messageId: message.id,
        type: "reasoning",
        reasoning,
      })
    }

    for (const toolCall of message.tool_calls ?? []) {
      if (toolCall.name === "task") {
        continue
      }
      const step: CoTToolCallStep = {
        id: toolCall.id,
        messageId: message.id,
        type: "toolCall",
        name: toolCall.name,
        args: toolCall.args,
      }
      if (toolCall.id) {
        const toolCallResult = findToolCallResult(toolCall.id, messages)
        if (toolCallResult) {
          step.result = parseMaybeJson(toolCallResult)
        }
      }
      steps.push(step)
    }
  }

  return steps
}

function parseMaybeJson(value: string): string | Record<string, unknown> | unknown[] {
  try {
    const parsed = JSON.parse(value) as unknown
    if (Array.isArray(parsed) || isRecord(parsed)) {
      return parsed
    }
    return value
  } catch {
    return value
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null
}
