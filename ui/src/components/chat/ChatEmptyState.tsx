import { Suggestion, Suggestions } from "@/components/ai-elements/suggestion"
import { Sparkles } from "lucide-react"
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty"

interface ChatEmptyStateProps {
  onSuggestion?: (suggestion: string) => void
}

const SUGGESTIONS = [
  "帮我分析一个 Python 项目的架构",
  "制定一个两周交付的软件开发计划",
  "评审一段代码并给出改进建议",
]

export function ChatEmptyState({ onSuggestion }: ChatEmptyStateProps) {
  return (
    <Empty className="flex h-full flex-col items-center justify-center text-center">
      <EmptyHeader>
        <EmptyMedia variant="icon">
          <Sparkles />
        </EmptyMedia>
        <EmptyTitle>开始对话</EmptyTitle>
        <EmptyDescription>
          在下方输入消息，SwarmMind 将基于组织上下文为你解答。
        </EmptyDescription>
      </EmptyHeader>
      {onSuggestion && (
        <Suggestions className="w-full flex-wrap justify-center">
          {SUGGESTIONS.map((s) => (
            <Suggestion key={s} suggestion={s} onClick={onSuggestion} />
          ))}
        </Suggestions>
      )}
    </Empty>
  )
}
