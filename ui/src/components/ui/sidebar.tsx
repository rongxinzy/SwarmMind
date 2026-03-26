"use client";

import * as React from "react";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  FolderKanban,
  Search,
  Bot,
  Library,
  Plus,
  ChevronDown,
  Menu,
  Sparkles,
  Clock,
  Compass,
  Home,
} from "lucide-react";

export type SidebarView = "tasks" | "projects" | "search" | "agents" | "library";

export const VIEW_LABELS: Record<SidebarView, string> = {
  tasks: "新建任务",
  projects: "项目",
  search: "搜索",
  agents: "Agent 团队",
  library: "知识库",
};

const RECENT_ITEMS = [
  { label: "Q3 财务异常分析报告", time: "1h" },
  { label: "客户续费风险评估", time: "3h" },
  { label: "项目交付延期根因分析", time: "昨天" },
  { label: "本月成本异常溯源", time: "昨天" },
  { label: "销售漏斗转化分析", time: "周一" },
  { label: "竞品功能对比调研", time: "周一" },
];

interface SidebarProps {
  activeView: SidebarView;
  onViewChange: (view: SidebarView) => void;
  pageTitle?: string;
}

const navItems: { value: SidebarView; label: string; icon: React.ReactNode; badge?: string }[] = [
  { value: "tasks", label: "工作台", icon: <Home className="w-4 h-4" /> },
  { value: "projects", label: "项目", icon: <FolderKanban className="w-4 h-4" />, badge: "3" },
  { value: "search", label: "搜索", icon: <Search className="w-4 h-4" /> },
  { value: "agents", label: "Agent 团队", icon: <Bot className="w-4 h-4" /> },
  { value: "library", label: "知识库", icon: <Library className="w-4 h-4" /> },
];

const featureItems: { label: string; icon: React.ReactNode; badge: string; highlight?: boolean }[] = [
  { label: "技能中心", icon: <Sparkles className="w-4 h-4" />, badge: "12", highlight: true },
  { label: "定时任务", icon: <Clock className="w-4 h-4" />, badge: "2", highlight: true },
  { label: "深度调研", icon: <Compass className="w-4 h-4" />, badge: "新", highlight: true },
];

const XIcon = () => (
  <motion.svg
    width="16"
    height="16"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
  >
    <motion.line x1="18" y1="6" x2="6" y2="18" />
    <motion.line x1="6" y1="6" x2="18" y2="18" />
  </motion.svg>
);

const SwarmLogo = ({ className = "w-5 h-5" }: { className?: string }) => (
  <svg className={className} viewBox="0 0 13 13" fill="none">
    <path d="M6.5 1L11.5 4v5L6.5 12 1.5 9V4L6.5 1Z" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round"/>
    <circle cx="6.5" cy="6.5" r="1.5" fill="currentColor"/>
  </svg>
);

export function Sidebar({ activeView, onViewChange, pageTitle }: SidebarProps) {
  const [isOpen, setIsOpen] = React.useState(false);

  const sidebarContent = (
    <div className="flex flex-col h-full">
      {/* Logo */}
      <div className="h-[52px] flex items-center gap-2.5 px-3.5 border-b border-sidebar-border">
        <div className="w-[22px] h-[22px] bg-foreground rounded-md flex items-center justify-center flex-shrink-0">
          <SwarmLogo className="w-3.5 h-3.5 text-background" />
        </div>
        <span className="text-sm font-semibold text-foreground tracking-tight">SwarmMind</span>
        <span className="ml-auto text-[10px] text-muted-foreground font-mono tracking-wider">v0.1</span>
      </div>

      {/* New Task Button */}
      <div className="p-2.5 pb-2">
        <Button
          onClick={() => onViewChange("tasks")}
          className="w-full justify-start gap-2 bg-primary text-primary-foreground hover:bg-primary/90 font-medium text-[13px]"
          size="sm"
        >
          <Plus className="w-3.5 h-3.5" />
          新建任务
        </Button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto px-1.5 py-1">
        {/* 导航 */}
        <div className="px-2 pt-1 pb-0">
          <p className="text-[10px] font-medium tracking-widest uppercase text-muted-foreground/70 opacity-60 pb-1 px-2">导航</p>
          <div className="space-y-0.5">
            {navItems.map((item) => (
              <button
                key={item.value}
                onClick={() => onViewChange(item.value)}
                className={cn(
                  "w-full flex items-center gap-2 px-2 py-1.5 rounded-md text-[13px] transition-colors",
                  activeView === item.value
                    ? "bg-sidebar-accent text-sidebar-accent-foreground font-medium"
                    : "text-muted-foreground hover:bg-secondary hover:text-foreground"
                )}
              >
                <span className="opacity-60">{item.icon}</span>
                <span>{item.label}</span>
                {item.badge && (
                  <span className="ml-auto text-[10px] font-mono px-1.5 py-0.5 rounded text-muted-foreground">
                    {item.badge}
                  </span>
                )}
              </button>
            ))}
          </div>
        </div>

        <div className="h-px bg-sidebar-border my-2 mx-2" />

        {/* 功能 */}
        <div className="px-2 pt-0 pb-1">
          <p className="text-[10px] font-medium tracking-widest uppercase text-muted-foreground/70 opacity-60 pb-1 px-2">功能</p>
          <div className="space-y-0.5">
            {featureItems.map((item) => (
              <button
                key={item.label}
                onClick={() => {}}
                className="w-full flex items-center gap-2 px-2 py-1.5 rounded-md text-[13px] text-muted-foreground hover:bg-secondary hover:text-foreground transition-colors"
              >
                <span className="opacity-60">{item.icon}</span>
                <span>{item.label}</span>
                <span className="ml-auto text-[10px] font-mono px-1.5 py-0.5 rounded bg-secondary text-foreground">
                  {item.badge}
                </span>
              </button>
            ))}
          </div>
        </div>

        <div className="h-px bg-sidebar-border my-2 mx-2" />

        {/* Recent */}
        <div className="px-2 pt-0">
          <p className="text-[10px] font-medium tracking-widest uppercase text-muted-foreground/70 opacity-60 pb-1 px-2">最近</p>
          <div className="space-y-0.5">
            {RECENT_ITEMS.map((item) => (
              <button
                key={item.label}
                onClick={() => {}}
                className="w-full flex items-center gap-2 px-2 py-1.5 rounded-md text-[13px] text-muted-foreground hover:bg-secondary hover:text-foreground transition-colors"
              >
                <span className="truncate flex-1 text-left">{item.label}</span>
                <span className="text-[10px] font-mono text-muted-foreground/60 flex-shrink-0">{item.time}</span>
              </button>
            ))}
          </div>
        </div>
      </nav>

      {/* Footer */}
      <div className="p-2 border-t border-sidebar-border">
        <button className="w-full flex items-center gap-2 px-2 py-1.5 rounded-md text-[13px] text-muted-foreground hover:bg-secondary hover:text-foreground transition-colors">
          <div className="w-6 h-6 bg-secondary rounded-full flex items-center justify-center text-[10px] font-semibold border border-border">
            容
          </div>
          <div className="flex-1 text-left">
            <div className="text-[13px] font-medium text-foreground leading-tight">容芯开源组</div>
            <div className="text-[11px] text-muted-foreground">Pro 计划</div>
          </div>
          <ChevronDown className="w-3.5 h-3.5 opacity-50" />
        </button>
      </div>
    </div>
  );

  return (
    <>
      {/* Mobile Sidebar Overlay */}
      <AnimatePresence>
        {isOpen && (
          <>
            {/* Backdrop */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/50 z-40 md:hidden"
              onClick={() => setIsOpen(false)}
            />
            {/* Mobile Sidebar */}
            <motion.div
              initial={{ x: "-100%" }}
              animate={{ x: 0 }}
              exit={{ x: "-100%" }}
              transition={{ type: "spring", damping: 25, stiffness: 200 }}
              className="fixed inset-y-0 left-0 z-50 w-[220px] bg-sidebar border-r border-sidebar-border md:hidden"
            >
              {/* Mobile Header */}
              <div className="flex items-center justify-between p-3.5 border-b border-sidebar-border">
                <div className="flex items-center gap-2">
                  <div className="w-[22px] h-[22px] bg-foreground rounded-md flex items-center justify-center">
                    <SwarmLogo className="w-3.5 h-3.5 text-background" />
                  </div>
                  <span className="text-foreground font-semibold text-sm">SwarmMind</span>
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => setIsOpen(false)}
                  className="text-muted-foreground hover:text-foreground"
                >
                  <XIcon />
                </Button>
              </div>
              {sidebarContent}
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* Desktop Sidebar */}
      <div className="hidden md:flex flex-col fixed top-0 left-0 h-full w-[220px] bg-sidebar border-r border-sidebar-border">
        {sidebarContent}
      </div>

      {/* Mobile Header Bar */}
      <div className="md:hidden fixed top-0 left-0 right-0 z-30 bg-sidebar border-b border-sidebar-border">
        <div className="flex items-center justify-between p-3.5">
          <div className="flex items-center gap-2">
            <div className="w-[22px] h-[22px] bg-foreground rounded-md flex items-center justify-center">
              <SwarmLogo className="w-3.5 h-3.5 text-background" />
            </div>
            <span className="text-foreground font-semibold text-sm">{pageTitle || "SwarmMind"}</span>
          </div>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setIsOpen(true)}
            className="text-muted-foreground hover:text-foreground"
          >
            <Menu />
          </Button>
        </div>
      </div>
    </>
  );
}
