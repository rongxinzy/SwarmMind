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
  selectedRowClassName: string;
  icon: typeof Zap;
}[] = [
  {
    id: "flash",
    label: "Flash",
    description: "最快回复，不展开推理",
    accentClassName: "border-[var(--status-running-border)] bg-[var(--status-running-bg)] text-[var(--status-running)]",
    selectedRowClassName: "bg-[var(--status-running-bg)] text-[var(--status-running)]",
    icon: Zap,
  },
  {
    id: "thinking",
    label: "Thinking",
    description: "保留推理过程，单轮深入分析",
    accentClassName: "border-[var(--accent-border)] bg-[var(--accent-soft)] text-[var(--accent)]",
    selectedRowClassName: "bg-[var(--accent-soft)] text-[var(--accent)]",
    icon: Lightbulb,
  },
  {
    id: "pro",
    label: "Pro",
    description: "先规划再执行",
    accentClassName: "border-[var(--status-done-border)] bg-[var(--status-done-bg)] text-[var(--status-done)]",
    selectedRowClassName: "bg-[var(--status-done-bg)] text-[var(--status-done)]",
    icon: GraduationCap,
  },
  {
    id: "ultra",
    label: "Ultra",
    description: "启用完整协作流程",
    accentClassName: "border-[var(--status-approval-border)] bg-[var(--status-approval-bg)] text-[var(--status-approval)]",
    selectedRowClassName: "bg-[var(--status-approval-bg)] text-[var(--status-approval)]",
    icon: Rocket,
  },
];

export function ModePicker({
  selected,
  onSelect,
  placement = "top",
}: {
  selected: ConversationMode;
  onSelect: (id: ConversationMode) => void;
  placement?: "top" | "bottom";
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
          "group flex h-9 items-center gap-2 rounded-[18px] border px-2.5 py-1.5 text-left transition-all duration-200 hover:border-border focus-visible:border-border focus-visible:ring-2 focus-visible:ring-accent/40",
          current.accentClassName,
        )}
      >
        <span className="flex size-6 items-center justify-center rounded-[10px] border border-black/5 bg-card">
          <CurrentIcon className="size-3" />
        </span>
        <span className="min-w-0">
          <span className="block text-[11px] leading-4 font-semibold">{current.label}</span>
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
              className={cn(
                "absolute left-0 z-50 w-[220px] rounded-[22px] border border-border bg-card p-2 shadow-[var(--shadow-popover)]",
                placement === "top" ? "bottom-full mb-2.5" : "top-full mt-2.5",
              )}
            >
              <div className="mb-1.5 px-1.5">
                <p className="text-[11px] text-muted-foreground">执行模式</p>
                <p className="text-[12px] text-foreground">选择这轮临时会话的执行方式</p>
              </div>
              <div className="space-y-0.5">
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
                        "flex w-full items-center gap-2.5 rounded-[16px] px-3 py-2 text-left transition-colors",
                        isSelected
                          ? mode.selectedRowClassName
                          : "text-foreground hover:bg-surface-hover",
                      )}
                    >
                      <span
                        className={cn(
                          "flex size-7 shrink-0 items-center justify-center rounded-[10px] bg-background/90",
                          isSelected ? "text-current" : "text-muted-foreground",
                        )}
                      >
                        <Icon className="size-3.5" />
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="text-[12px] font-semibold">{mode.label}</span>
                        <span className="mt-0.5 block text-[10px] leading-4 opacity-75">{mode.description}</span>
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
  placement = "top",
}: {
  models: RuntimeModelOptionLike[];
  selected: string;
  onSelect: (id: string) => void;
  isLoading: boolean;
  loadError: string | null;
  onRetry: () => void;
  placement?: "top" | "bottom";
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
        className="flex h-9 items-center gap-1.5 rounded-[18px] border border-transparent bg-transparent px-2.5 text-[11px] text-muted-foreground transition-all duration-200 hover:border-border hover:bg-surface-hover hover:text-foreground focus-visible:border-border focus-visible:ring-2 focus-visible:ring-accent/40"
      >
        {isLoading ? <Loader2 className="size-3.5 animate-spin" /> : <Sparkles className="size-3.5" />}
        <span className="max-w-[124px] truncate">{currentLabel}</span>
        {!isDisabled ? <ChevronDown className="size-3 shrink-0" /> : null}
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
              className={cn(
                "absolute left-0 z-50 w-[190px] overflow-hidden rounded-[20px] border border-border bg-card p-1.5 shadow-[var(--shadow-popover)]",
                placement === "top" ? "bottom-full mb-2" : "top-full mt-2",
              )}
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
                    "flex min-h-9 w-full items-center gap-2 rounded-[16px] px-3 py-2 text-[12px] transition-colors",
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
