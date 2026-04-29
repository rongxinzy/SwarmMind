"use client";

import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  ChevronDown,
  GraduationCap,
  Lightbulb,
  Loader2,
  Rocket,
  Sparkles,
  Zap,
} from "lucide-react";

import { cn } from "@/lib/utils";

type ConversationMode = "flash" | "thinking" | "pro" | "ultra";

interface RuntimeModelOptionLike {
  name: string;
  display_name?: string | null;
}

const MODE_OPTIONS: {
  id: ConversationMode;
  label: string;
  description: string;
  accentClassName: string;
  icon: typeof Zap;
}[] = [
  {
    id: "flash",
    label: "Flash",
    description: "最快回复，不展开推理",
    accentClassName: "border-[var(--status-running-border)] bg-[var(--status-running-bg)] text-[var(--status-running)]",
    icon: Zap,
  },
  {
    id: "thinking",
    label: "Thinking",
    description: "保留推理过程，单轮深入分析",
    accentClassName: "border-[var(--accent-border)] bg-[var(--accent-soft)] text-[var(--accent)]",
    icon: Lightbulb,
  },
  {
    id: "pro",
    label: "Pro",
    description: "先规划再执行",
    accentClassName: "border-[var(--status-done-border)] bg-[var(--status-done-bg)] text-[var(--status-done)]",
    icon: GraduationCap,
  },
  {
    id: "ultra",
    label: "Ultra",
    description: "启用完整协作流程",
    accentClassName: "border-[var(--status-approval-border)] bg-[var(--status-approval-bg)] text-[var(--status-approval)]",
    icon: Rocket,
  },
];

export function ModePicker({
  selected,
  onSelect,
}: {
  selected: ConversationMode;
  onSelect: (id: ConversationMode) => void;
}) {
  const [open, setOpen] = useState(false);
  const current = MODE_OPTIONS.find((mode) => mode.id === selected) ?? MODE_OPTIONS[0];
  const CurrentIcon = current.icon;

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => {
          setOpen((prev) => !prev);
        }}
        aria-label={`当前执行模式：${current.label}`}
        className={cn(
          "group flex min-h-10 items-center gap-2 rounded-lg border px-3 py-2 text-left transition-all duration-200 hover:border-border focus-visible:border-border focus-visible:ring-2 focus-visible:ring-accent/50",
          current.accentClassName,
        )}
      >
        <span className="flex size-6 items-center justify-center rounded-md border border-black/5 bg-card">
          <CurrentIcon className="size-3" />
        </span>
        <span className="min-w-0">
          <span className="block text-[10px] leading-4 font-semibold tracking-[0.08em]">{current.label}</span>
        </span>
        <ChevronDown
          className={cn(
            "size-3 shrink-0 transition-transform duration-200",
            open && "rotate-180",
          )}
        />
      </button>

      <AnimatePresence>
        {open && (
          <>
            <div
              className="fixed inset-0 z-40"
              onClick={() => {
                setOpen(false);
              }}
            />
            <motion.div
              initial={{ opacity: 0, y: 8, scale: 0.97 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 8, scale: 0.97 }}
              transition={{
                type: "spring",
                stiffness: 360,
                damping: 28,
                mass: 0.9,
              }}
              className="absolute bottom-full left-0 z-50 mb-2.5 w-[286px] rounded-[18px] border border-border bg-card p-2"
            >
              <div className="mb-1.5 px-1">
                <p className="text-[10px] tracking-[0.04em] text-muted-foreground">执行模式</p>
                <p className="text-[12px] text-foreground">选择这轮临时会话的执行方式</p>
              </div>
              <div className="space-y-1.5">
                {MODE_OPTIONS.map((mode, index) => {
                  const Icon = mode.icon;
                  const isSelected = mode.id === selected;

                  return (
                    <motion.button
                      key={mode.id}
                      type="button"
                      onClick={() => {
                        onSelect(mode.id);
                        setOpen(false);
                      }}
                      initial={{ opacity: 0, y: 6 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: index * 0.03 }}
                      className={cn(
                        "flex w-full items-start gap-2.5 rounded-[14px] border px-3 py-2.5 text-left transition-colors",
                        isSelected
                          ? cn("bg-card", mode.accentClassName)
                          : "border-border bg-card text-foreground hover:border-border-strong hover:bg-surface-hover",
                      )}
                    >
                      <span
                        className={cn(
                          "mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-md border bg-background",
                          isSelected ? "border-black/5" : "border-border/80",
                        )}
                      >
                        <Icon className="size-3.5" />
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="text-[12px] font-semibold">{mode.label}</span>
                        <span className="mt-0.5 block text-[11px] leading-4 opacity-80">{mode.description}</span>
                      </span>
                    </motion.button>
                  );
                })}
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
}

export function ModelPicker({
  models,
  selected,
  onSelect,
  isLoading,
  loadError,
  onRetry,
}: {
  models: RuntimeModelOptionLike[];
  selected: string;
  onSelect: (id: string) => void;
  isLoading: boolean;
  loadError: string | null;
  onRetry: () => void;
}) {
  const [open, setOpen] = useState(false);
  const current = models.find((model) => model.name === selected) ?? models[0];
  const currentLabel =
    current?.display_name || current?.name || (isLoading ? "加载模型..." : loadError ? "模型加载失败" : "未配置模型");
  const isDisabled = isLoading || (!loadError && models.length <= 1);

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => {
          if (loadError) {
            onRetry();
            return;
          }
          if (!isDisabled) {
            setOpen((prev) => !prev);
          }
        }}
        disabled={isDisabled}
        title={loadError ?? undefined}
        className="flex min-h-10 items-center gap-2 rounded-lg border border-transparent bg-transparent px-3 text-[11px] tracking-[0.04em] text-muted-foreground transition-all duration-200 hover:border-border hover:bg-surface-hover hover:text-foreground focus-visible:border-border focus-visible:ring-2 focus-visible:ring-accent/50"
      >
        {isLoading ? <Loader2 className="size-3.5 animate-spin" /> : <Sparkles className="size-3.5" />}
        <span className="max-w-[140px] truncate">{currentLabel}</span>
      </button>

      <AnimatePresence>
        {open && (
          <>
            <div
              className="fixed inset-0 z-40"
              onClick={() => {
                setOpen(false);
              }}
            />
            <motion.div
              initial={{ opacity: 0, y: 4, scale: 0.96 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 4, scale: 0.96 }}
              transition={{
                type: "spring",
                stiffness: 500,
                damping: 30,
                mass: 0.8,
              }}
              className="absolute bottom-full left-0 z-50 mb-2 w-[220px] overflow-hidden rounded-[16px] border border-border bg-card p-1.5"
            >
              {models.map((model) => (
                <button
                  key={model.name}
                  type="button"
                  onClick={() => {
                    onSelect(model.name);
                    setOpen(false);
                  }}
                  className={cn(
                    "flex min-h-11 w-full items-center gap-2 rounded-[14px] px-3 py-2 text-[13px] transition-colors",
                    model.name === selected
                      ? "bg-secondary text-foreground font-medium"
                      : "text-muted-foreground hover:bg-secondary hover:text-foreground",
                  )}
                >
                  <Sparkles className="size-3.5 shrink-0" />
                  <span className="truncate">{model.display_name || model.name}</span>
                </button>
              ))}
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
}
