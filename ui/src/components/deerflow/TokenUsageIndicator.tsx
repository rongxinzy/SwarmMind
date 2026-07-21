import type { Message } from "@langchain/langgraph-sdk"
import { Coins } from "lucide-react"
import { useMemo } from "react"

import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover"
import { accumulateUsage, formatTokenCount } from "@/core/deerflow/usage"
import { cn } from "@/lib/utils"

interface TokenUsageIndicatorProps {
  className?: string
  messages: Message[]
}

export function TokenUsageIndicator({
  className,
  messages,
}: TokenUsageIndicatorProps) {
  const usage = useMemo(() => accumulateUsage(messages), [messages])

  if (!usage) {
    return null
  }

  return (
    <Popover>
      <PopoverTrigger
        render={
          <button
            type="button"
            className={cn(
              "inline-flex items-center gap-1 rounded-full px-1.5 py-0.5 text-xs text-muted-foreground transition-colors hover:bg-[#f4f4f4] hover:text-[#3f3f3f] data-[popup-open]:bg-[#f4f4f4] data-[popup-open]:text-[#3f3f3f]",
              className,
            )}
            aria-label={`Token usage: ${formatTokenCount(usage.totalTokens)} total`}
          >
            <Coins className="size-3.5" />
            <span>{formatTokenCount(usage.totalTokens)}</span>
          </button>
        }
      />
      <PopoverContent side="bottom" align="end" className="w-44 gap-2 p-3">
        <div className="flex items-center gap-2 text-xs font-medium text-[#1a1a1a]">
          <Coins className="size-3.5 text-muted-foreground" />
          Token usage
        </div>
        <div className="space-y-1 text-xs text-[#5d5d5d]">
          <UsageRow label="Input" value={usage.inputTokens} />
          <UsageRow label="Output" value={usage.outputTokens} />
          <div className="border-t border-[#ececec] pt-1">
            <UsageRow label="Total" value={usage.totalTokens} strong />
          </div>
        </div>
      </PopoverContent>
    </Popover>
  )
}

function UsageRow({
  label,
  strong,
  value,
}: {
  label: string
  strong?: boolean
  value: number
}) {
  return (
    <div className="flex justify-between gap-4">
      <span>{label}</span>
      <span className={cn("font-mono", strong && "font-medium")}>
        {formatTokenCount(value)}
      </span>
    </div>
  )
}
