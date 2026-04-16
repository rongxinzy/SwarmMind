import { Zap, Lightbulb, GraduationCap, Rocket, WifiOff, ServerCrash, Clock, AlertCircle } from "lucide-react";
import type { ConversationMode, ChatErrorType } from "./types";

export const MODE_BADGE_TOKENS: Record<
  ConversationMode,
  {
    icon: typeof Zap;
    label: string;
    accent: string;
    streamLabel: string;
    statusLabel: string;
  }
> = {
  flash: {
    icon: Zap,
    label: "快速",
    accent:
      "border-[var(--status-running-border)] bg-[var(--status-running-bg)] text-[var(--status-running)]",
    streamLabel: "快速生成回复中…",
    statusLabel: "快速生成",
  },
  thinking: {
    icon: Lightbulb,
    label: "推理",
    accent:
      "border-[var(--status-chat-border)] bg-[var(--status-chat-bg)] text-[var(--status-chat)]",
    streamLabel: "深入分析中…",
    statusLabel: "深入分析",
  },
  pro: {
    icon: GraduationCap,
    label: "规划",
    accent:
      "border-[var(--status-done-border)] bg-[var(--status-done-bg)] text-[var(--status-done)]",
    streamLabel: "多步规划中…",
    statusLabel: "多步规划",
  },
  ultra: {
    icon: Rocket,
    label: "深度",
    accent:
      "border-[var(--status-approval-border)] bg-[var(--status-approval-bg)] text-[var(--status-approval)]",
    streamLabel: "深度推理与协作中…",
    statusLabel: "深度协作",
  },
};

export const ERROR_ICON_MAP: Record<ChatErrorType, typeof WifiOff> = {
  network: WifiOff,
  server: ServerCrash,
  timeout: Clock,
  unknown: AlertCircle,
};

export const ERROR_COPY: Record<ChatErrorType, { title: string; description: string }> = {
  network: {
    title: "网络连接失败",
    description: "网络不稳定，请检查连接后重试。",
  },
  server: {
    title: "服务端错误",
    description: "服务器暂时无法处理请求，请稍后再试。",
  },
  timeout: {
    title: "连接超时",
    description: "请求响应时间过长，请检查网络后重试。",
  },
  unknown: {
    title: "发生未知错误",
    description: "请求过程中出现意外错误，请重试。",
  },
};

export function classifyError(error: unknown): ChatErrorType {
  if (error instanceof Error) {
    const message = error.message.toLowerCase();
    if (message.includes("abort") || message.includes("timeout") || message.includes("timed out")) {
      return "timeout";
    }
    if (message.includes("network") || message.includes("fetch") || message.includes("failed to fetch")) {
      return "network";
    }
    if (message.includes("http 5") || message.includes("http 502") || message.includes("http 503") || message.includes("http 504")) {
      return "server";
    }
    if (message.includes("http 4")) {
      return "server";
    }
  }
  return "unknown";
}
