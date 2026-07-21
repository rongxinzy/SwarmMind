"use client"

import { ChevronUpIcon, ListTodoIcon } from "lucide-react"
import { useState } from "react"

import {
  QueueItem,
  QueueItemContent,
  QueueItemIndicator,
  QueueList,
} from "@/components/ai-elements/queue"
import { cn } from "@/lib/utils"
import type { ChatPlanStep } from "@/types/chat"

export function TodoList({
  className,
  collapsed: controlledCollapsed,
  hidden = false,
  onToggle,
  todos,
}: {
  className?: string
  collapsed?: boolean
  hidden?: boolean
  onToggle?: () => void
  todos: ChatPlanStep[]
}) {
  const [internalCollapsed, setInternalCollapsed] = useState(true)
  const isControlled = controlledCollapsed !== undefined
  const collapsed = isControlled ? controlledCollapsed : internalCollapsed
  const completedCount = todos.filter((todo) => todo.status === "completed").length
  const activeCount = todos.filter((todo) => todo.status === "in_progress").length

  const handleToggle = () => {
    if (isControlled) {
      onToggle?.()
    } else {
      setInternalCollapsed((prev) => !prev)
    }
  }

  return (
    <div
      className={cn(
        "flex h-fit w-full origin-bottom flex-col overflow-hidden rounded-xl border border-[#e7e7e4] bg-white/95 shadow-[0_10px_28px_rgba(20,20,20,0.04)] backdrop-blur-sm transition-all duration-200 ease-out",
        hidden ? "pointer-events-none translate-y-2 opacity-0" : "opacity-100",
        className,
      )}
    >
      <button
        className="flex min-h-9 shrink-0 cursor-pointer items-center justify-between border-b border-[#eeeeea] px-4 text-sm transition-all duration-300 ease-out hover:bg-[#fbfbfa]"
        onClick={handleToggle}
        type="button"
      >
        <div className="flex min-w-0 items-center gap-2 text-[#454545]">
          <ListTodoIcon className="size-4 shrink-0 text-[#7256f4]" />
          <span className="font-medium">To-dos</span>
          <span className="rounded-full bg-[#f4f2ff] px-2 py-0.5 text-[10px] font-medium text-[#7256f4]">
            {completedCount}/{todos.length}
          </span>
          {activeCount > 0 && (
            <span className="rounded-full bg-[#111] px-2 py-0.5 text-[10px] font-medium text-white">
              {activeCount} 运行中
            </span>
          )}
        </div>
        <ChevronUpIcon
          className={cn(
            "size-4 text-muted-foreground transition-transform duration-300 ease-out",
            collapsed ? "" : "rotate-180",
          )}
        />
      </button>
      <main
        className={cn(
          "flex grow bg-[#fbfbfa] px-2 transition-all duration-300 ease-out",
          collapsed ? "h-0 pb-0" : "h-32 pb-3 pt-2",
        )}
      >
        <QueueList className="mt-0 w-full rounded-lg bg-white">
          {todos.map((todo, index) => (
            <QueueItem
              key={`${index}-${todo.content}`}
              className="rounded-lg px-3 py-1.5 hover:bg-[#fbfbfa]"
            >
              <div className="flex min-w-0 items-center gap-2">
                <QueueItemIndicator
                  className={cn(
                    "shrink-0",
                    todo.status === "in_progress" && "border-[#7256f4] bg-[#7256f4] shadow-[0_0_0_3px_rgba(114,86,244,0.12)]",
                    todo.status === "pending" && "border-[#cfcfcf] bg-white",
                  )}
                  completed={todo.status === "completed"}
                />
                <QueueItemContent
                  className={cn(
                    "min-w-0 text-xs",
                    todo.status === "in_progress" && "font-medium text-[#242424]",
                    todo.status === "pending" && "text-[#666]",
                  )}
                  completed={todo.status === "completed"}
                >
                  {todo.content}
                </QueueItemContent>
              </div>
            </QueueItem>
          ))}
        </QueueList>
      </main>
    </div>
  )
}
