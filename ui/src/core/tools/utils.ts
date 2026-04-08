import type { AIMessage } from "@langchain/langgraph-sdk";

import { hasToolCalls } from "../messages/utils";

interface ToolCall {
  id?: string;
  name: string;
  args: Record<string, unknown>;
}

export function explainLastToolCall(message: AIMessage): string {
  if (hasToolCalls(message)) {
    const lastToolCall = message.tool_calls![message.tool_calls!.length - 1] as ToolCall;
    return explainToolCall(lastToolCall);
  }
  return "思考中...";
}

export function explainToolCall(toolCall: ToolCall): string {
  if (toolCall.name === "web_search" || toolCall.name === "image_search") {
    return `搜索: ${toolCall.args.query as string}`;
  } else if (toolCall.name === "web_fetch") {
    return "获取网页内容";
  } else if (toolCall.name === "present_files") {
    return "展示文件";
  } else if (toolCall.args.description) {
    return toolCall.args.description as string;
  } else {
    return `使用工具: ${toolCall.name}`;
  }
}
