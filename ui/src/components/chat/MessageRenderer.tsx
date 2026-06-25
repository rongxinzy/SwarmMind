import {
  Artifact,
  ArtifactDescription,
  ArtifactHeader,
  ArtifactTitle,
} from "@/components/ai-elements/artifact"
import {
  Confirmation,
  ConfirmationAction,
  ConfirmationActions,
  ConfirmationTitle,
} from "@/components/ai-elements/confirmation"
import {
  Message,
  MessageActions,
  MessageAction,
  MessageContent,
  MessageResponse,
} from "@/components/ai-elements/message"
import {
  Reasoning,
  ReasoningContent,
  ReasoningTrigger,
} from "@/components/ai-elements/reasoning"
import {
  Tool,
  ToolContent,
  ToolHeader,
  ToolInput,
  ToolOutput,
} from "@/components/ai-elements/tool"
import { CopyIcon, RefreshCcwIcon } from "lucide-react"
import type { ChatMessage, MessagePart, ReasoningPart, TextPart, ToolInvocationPart } from "@/types/chat"

interface MessageRendererProps {
  message: ChatMessage
  isLast: boolean
  isStreaming: boolean
  onReload?: () => void
  onOpenApprovals?: () => void
}

export function MessageRenderer({ message, isLast, isStreaming, onReload, onOpenApprovals }: MessageRendererProps) {
  const reasoningParts = message.parts.filter((p): p is ReasoningPart => p.type === "reasoning")
  const reasoningText = reasoningParts.map((p) => p.text).join("\n\n")
  const isReasoningStreaming = isLast && isStreaming && reasoningParts.some((p) => p.state === "streaming")

  return (
    <Message from={message.role} className="group">
      <MessageContent>
        {reasoningText && (
          <Reasoning isStreaming={isReasoningStreaming}>
            <ReasoningTrigger />
            <ReasoningContent>{reasoningText}</ReasoningContent>
          </Reasoning>
        )}
        {message.parts.map((part, i) => (
          <PartRenderer key={`${message.id}-${i}`} part={part} onOpenApprovals={onOpenApprovals} />
        ))}
      </MessageContent>
      {message.role === "assistant" && isLast && !isStreaming && (
        <MessageActions>
          <MessageAction
            label="复制"
            onClick={() => {
              const text = message.parts
                .filter((p): p is TextPart => p.type === "text")
                .map((p) => p.text)
                .join("\n")
              void navigator.clipboard.writeText(text)
            }}
          >
            <CopyIcon className="size-3" />
          </MessageAction>
          {onReload && (
            <MessageAction label="重试" onClick={onReload}>
              <RefreshCcwIcon className="size-3" />
            </MessageAction>
          )}
        </MessageActions>
      )}
    </Message>
  )
}

interface PartRendererProps {
  part: MessagePart
  onOpenApprovals?: () => void
}

function PartRenderer({ part, onOpenApprovals }: PartRendererProps) {
  switch (part.type) {
    case "text":
      return <MessageResponse>{part.text}</MessageResponse>

    case "tool-invocation": {
      const toolPart = part as ToolInvocationPart
      const outputNode = toolPart.output
        ? formatToolOutput(toolPart.output)
        : null
      return (
        <Tool defaultOpen={toolPart.state !== "input-streaming"}>
          <ToolHeader
            type="dynamic-tool"
            state={toolPart.state}
            toolName={toolPart.toolName}
          />
          <ToolContent>
            {toolPart.input && Object.keys(toolPart.input).length > 0 && (
              <ToolInput input={toolPart.input} />
            )}
            <ToolOutput output={outputNode} errorText={undefined} />
          </ToolContent>
        </Tool>
      )
    }

    case "approval-request":
      return (
        <Confirmation approval={{ id: part.approvalId }} state="approval-requested">
          <ConfirmationTitle>
            需要审批：{part.capability}（风险等级：{part.riskTier}）
          </ConfirmationTitle>
          <ConfirmationActions>
            {onOpenApprovals && (
              <ConfirmationAction variant="outline" onClick={onOpenApprovals}>
                去审批中心
              </ConfirmationAction>
            )}
          </ConfirmationActions>
        </Confirmation>
      )

    case "artifact":
      return (
        <Artifact>
          <ArtifactHeader>
            <ArtifactTitle>{part.name || "产物"}</ArtifactTitle>
            {part.artifactType && <ArtifactDescription>{part.artifactType}</ArtifactDescription>}
          </ArtifactHeader>
        </Artifact>
      )

    default:
      return null
  }
}

/**
 * 将工具输出对象渲染为 MessageResponse（markdown）。
 * 避免用裸 <div> + Tailwind 复刻键值展示——交由 ai-elements 的 MessageResponse 原语处理。
 */
function formatToolOutput(output: Record<string, unknown>): React.ReactNode {
  const text = Object.entries(output)
    .map(([k, v]) => `- **${k}**: ${typeof v === "string" ? v : JSON.stringify(v)}`)
    .join("\n")
  return <MessageResponse>{text || "（无输出）"}</MessageResponse>
}
