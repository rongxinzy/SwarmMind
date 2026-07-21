"use client"

import type { Message } from "@langchain/langgraph-sdk"
import {
  CheckCircleIcon,
  ChevronUpIcon,
  ClipboardListIcon,
  Loader2Icon,
  LightbulbIcon,
  XCircleIcon,
} from "lucide-react"
import { useMemo, useState } from "react"

import {
  ChainOfThought,
  ChainOfThoughtContent,
  ChainOfThoughtStep,
} from "@/components/ai-elements/chain-of-thought"
import { Shimmer } from "@/components/ai-elements/shimmer"
import { Button } from "@/components/ui/button"
import {
  extractReasoningContentFromMessage,
  findToolCallResult,
} from "@/core/deerflow/messages"
import { cn } from "@/lib/utils"

import { MarkdownContent } from "./MarkdownContent"

type SubtaskStatus = "in_progress" | "completed" | "failed"

interface SubtaskItem {
  id?: string
  messageId?: string
  title: string
  prompt?: string
  status: SubtaskStatus
  result?: string
  error?: string
}

export function SubtaskGroup({
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
  const reasoningItems = useMemo(() => collectReasoning(messages), [messages])
  const subtasks = useMemo(() => collectSubtasks(messages), [messages])

  if (reasoningItems.length === 0 && subtasks.length === 0) {
    return null
  }

  return (
    <div className={cn("flex w-full flex-col gap-2", className)}>
      {reasoningItems.map((item) => (
        <ReasoningCard
          key={item.id ?? item.content}
          conversationId={conversationId}
          content={item.content}
          isLoading={isLoading}
          onArtifactSelect={onArtifactSelect}
        />
      ))}
      {subtasks.map((task) => (
        <SubtaskCard
          key={task.id ?? `${task.messageId}-${task.title}`}
          conversationId={conversationId}
          isLoading={isLoading}
          task={task}
          onArtifactSelect={onArtifactSelect}
        />
      ))}
    </div>
  )
}

function ReasoningCard({
  conversationId,
  content,
  isLoading,
  onArtifactSelect,
}: {
  conversationId?: string
  content: string
  isLoading: boolean
  onArtifactSelect?: (file: string) => void
}) {
  const [open, setOpen] = useState(false)

  return (
    <ChainOfThought
      className="relative w-full gap-2 overflow-hidden rounded-xl border border-[#e7e7e4] bg-white p-1 shadow-[0_8px_24px_rgba(20,20,20,0.03)]"
      open={open}
    >
      <Button
        className="w-full items-start justify-start rounded-lg text-left text-[#3d3d3d] hover:bg-[#f7f7f5]"
        variant="ghost"
        onClick={() => setOpen((current) => !current)}
      >
        <div className="flex w-full items-center justify-between">
          <ChainOfThoughtStep
            className="font-normal"
            label="子任务规划"
            icon={LightbulbIcon}
          />
          <ChevronUpIcon
            className={cn("size-4 text-muted-foreground", open ? "" : "rotate-180")}
          />
        </div>
      </Button>
      {open && (
        <ChainOfThoughtContent className="px-3 pb-3">
          <ChainOfThoughtStep
            className="rounded-lg bg-[#fbfbfa] px-2.5 py-2 text-[#4b4b4b]"
            label={
              <MarkdownContent
                conversationId={conversationId}
                content={content}
                isLoading={isLoading}
                onArtifactSelect={onArtifactSelect}
              />
            }
          />
        </ChainOfThoughtContent>
      )}
    </ChainOfThought>
  )
}

function SubtaskCard({
  conversationId,
  isLoading,
  task,
  onArtifactSelect,
}: {
  conversationId?: string
  isLoading: boolean
  task: SubtaskItem
  onArtifactSelect?: (file: string) => void
}) {
  const [open, setOpen] = useState(task.status === "in_progress")
  const statusLabel = taskStatusLabel(task.status)

  return (
    <ChainOfThought
      className={cn(
        "relative w-full gap-2 overflow-hidden rounded-xl border border-[#e7e7e4] bg-white p-1 shadow-[0_8px_24px_rgba(20,20,20,0.03)]",
        task.status === "in_progress" && "border-[#ded8ff] shadow-[0_12px_34px_rgba(114,86,244,0.08)]",
      )}
      open={open}
    >
      {task.status === "in_progress" && (
        <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-[#7256f4] via-[#a978ff] to-[#ff80b5]" />
      )}
      <Button
        className="w-full items-start justify-start rounded-lg text-left hover:bg-[#f7f7f5]"
        variant="ghost"
        onClick={() => setOpen((current) => !current)}
      >
        <div className="flex w-full items-center justify-between gap-3">
          <ChainOfThoughtStep
            className="min-w-0 font-normal"
            label={
              task.status === "in_progress" && isLoading ? (
                <Shimmer duration={3} spread={3}>
                  {task.title}
                </Shimmer>
              ) : (
                <span className="line-clamp-2">{task.title}</span>
              )
            }
            icon={ClipboardListIcon}
          />
          <div className="flex shrink-0 items-center gap-2">
            <span
              className={cn(
                "inline-flex h-5 items-center gap-1 rounded-full border px-2 text-[10px] font-medium leading-none",
                task.status === "completed" && "border-[#dfe8df] bg-[#f7fbf7] text-[#2f7d32]",
                task.status === "failed" && "border-[#f1cccc] bg-[#fff7f7] text-destructive",
                task.status === "in_progress" && "border-[#ded8ff] bg-[#fbfbff] text-[#7256f4]",
              )}
            >
              <TaskStatusIcon status={task.status} />
              {statusLabel}
            </span>
            <ChevronUpIcon
              className={cn("size-4 text-muted-foreground", open ? "" : "rotate-180")}
            />
          </div>
        </div>
      </Button>
      {open && (
        <ChainOfThoughtContent className="px-3 pb-4">
          {task.prompt && (
            <ChainOfThoughtStep
              className="rounded-lg bg-[#fbfbfa] px-2.5 py-2 text-[#555]"
              label={
                <MarkdownContent
                  conversationId={conversationId}
                  content={task.prompt}
                  isLoading={false}
                  onArtifactSelect={onArtifactSelect}
                />
              }
            />
          )}
          {task.status === "in_progress" && (
            <ChainOfThoughtStep
              className="rounded-lg bg-[#fbfbff] px-2.5 py-2 text-[#1f1f1f] shadow-[inset_2px_0_0_#7256f4]"
              label="子任务执行中"
              icon={Loader2Icon}
              status="active"
            />
          )}
          {task.status === "completed" && (
            <>
              <ChainOfThoughtStep
                className="rounded-lg bg-[#f7fbf7] px-2.5 py-2 text-[#2f7d32]"
                label="子任务已完成"
                icon={CheckCircleIcon}
              />
              {task.result && (
                <ChainOfThoughtStep
                  className="rounded-lg bg-[#fbfbfa] px-2.5 py-2 text-[#4b4b4b]"
                  label={
                    <MarkdownContent
                      conversationId={conversationId}
                      content={task.result}
                      isLoading={false}
                      onArtifactSelect={onArtifactSelect}
                    />
                  }
                />
              )}
            </>
          )}
          {task.status === "failed" && (
            <ChainOfThoughtStep
              className="rounded-lg bg-[#fff7f7] px-2.5 py-2"
              label={<span className="text-destructive">{task.error ?? "子任务失败"}</span>}
              icon={XCircleIcon}
              status="active"
            />
          )}
        </ChainOfThoughtContent>
      )}
    </ChainOfThought>
  )
}

function TaskStatusIcon({ status }: { status: SubtaskStatus }) {
  if (status === "completed") {
    return <CheckCircleIcon className="size-3" data-icon="inline-start" />
  }
  if (status === "failed") {
    return <XCircleIcon className="size-3" data-icon="inline-start" />
  }
  return <Loader2Icon className="size-3 animate-spin" data-icon="inline-start" />
}

function collectReasoning(messages: Message[]) {
  return messages.flatMap((message) => {
    const content = extractReasoningContentFromMessage(message)
    return content ? [{ id: message.id, content }] : []
  })
}

function collectSubtasks(messages: Message[]) {
  const tasks: SubtaskItem[] = []

  for (const message of messages) {
    if (message.type !== "ai") {
      continue
    }

    for (const toolCall of message.tool_calls ?? []) {
      if (toolCall.name !== "task") {
        continue
      }

      const args = isRecord(toolCall.args) ? toolCall.args : {}
      const rawResult = toolCall.id ? findToolCallResult(toolCall.id, messages) : undefined
      const parsed = parseTaskResult(rawResult)

      tasks.push({
        id: toolCall.id,
        messageId: message.id,
        title: taskTitle(args),
        prompt: stringArg(args.prompt),
        ...parsed,
      })
    }
  }

  return tasks
}

function taskTitle(args: Record<string, unknown>) {
  const description = stringArg(args.description)
  if (description) {
    return description
  }
  const prompt = stringArg(args.prompt)
  if (prompt) {
    return prompt.split("\n").find((line) => line.trim())?.trim() ?? "新的协作分工"
  }
  return "新的协作分工"
}

function parseTaskResult(result: string | undefined): Pick<SubtaskItem, "status" | "result" | "error"> {
  if (!result) {
    return { status: "in_progress" }
  }

  const succeeded = result.match(/^Task Succeeded\.\s*Result:\s*([\s\S]*)$/i)
  if (succeeded) {
    return { status: "completed", result: succeeded[1]?.trim() || "完成" }
  }

  const failed = result.match(/^Task failed\.?\s*([\s\S]*)$/i)
  if (failed) {
    return { status: "failed", error: failed[1]?.trim() || "子任务失败" }
  }

  if (/timed out/i.test(result)) {
    return { status: "failed", error: result.trim() }
  }

  return { status: "completed", result: result.trim() }
}

function taskStatusLabel(status: SubtaskStatus) {
  switch (status) {
    case "completed":
      return "完成"
    case "failed":
      return "失败"
    case "in_progress":
      return "执行中"
  }
}

function stringArg(value: unknown) {
  return typeof value === "string" && value.trim() ? value.trim() : undefined
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null
}
