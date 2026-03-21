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
} from "lucide-react";

export type SidebarView = "tasks" | "projects" | "search" | "agents" | "library";

export const VIEW_LABELS: Record<SidebarView, string> = {
  tasks: "New Task",
  projects: "Projects",
  search: "Search",
  agents: "Agents",
  library: "Library",
};

interface Conversation {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

interface SidebarProps {
  activeView: SidebarView;
  onViewChange: (view: SidebarView) => void;
  pageTitle?: string;
  onConversationSelect?: (conversationId: string) => void;
  activeConversationId?: string;
  conversationRefreshTrigger?: number;
}

const navItems: { value: SidebarView; label: string; icon: React.ReactNode }[] = [
  { value: "tasks", label: "New Task", icon: <Plus className="w-5 h-5" /> },
  { value: "projects", label: "Projects", icon: <FolderKanban className="w-5 h-5" /> },
  { value: "search", label: "Search", icon: <Search className="w-5 h-5" /> },
  { value: "agents", label: "Agents", icon: <Bot className="w-5 h-5" /> },
  { value: "library", label: "Library", icon: <Library className="w-5 h-5" /> },
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

function CollapsibleSection({
  title,
  children,
  defaultOpen = false,
}: {
  title: string;
  children: React.ReactNode;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = React.useState(defaultOpen);

  return (
    <div className="mb-2">
      <button
        className="w-full flex items-center justify-between py-2 px-3 rounded-lg hover:bg-neutral-800 transition-colors"
        onClick={() => setOpen(!open)}
      >
        <span className="text-sm font-medium text-neutral-300">{title}</span>
        <motion.div animate={{ rotate: open ? 180 : 0 }} transition={{ duration: 0.2 }}>
          <ChevronDown className="w-4 h-4 text-neutral-500" />
        </motion.div>
      </button>
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="pl-3 pr-1 py-1">{children}</div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export function Sidebar({ activeView, onViewChange, pageTitle, onConversationSelect, activeConversationId, conversationRefreshTrigger }: SidebarProps) {
  const [isOpen, setIsOpen] = React.useState(false);
  const [conversations, setConversations] = React.useState<Conversation[]>([]);

  React.useEffect(() => {
    if (activeView === "tasks") {
      fetchConversations();
    }
  }, [activeView, conversationRefreshTrigger]);

  const fetchConversations = async () => {
    try {
      const res = await fetch("/conversations");
      if (res.ok) {
        const data = await res.json();
        setConversations(data.items || []);
      }
    } catch (e) {
      console.error("Failed to fetch conversations:", e);
    }
  };

  const handleConversationClick = (convId: string) => {
    onConversationSelect?.(convId);
  };

  const sidebarContent = (
    <div className="flex flex-col h-full">
      {/* Navigation */}
      <nav className="flex-1 p-3 overflow-y-auto">
        {/* Primary Navigation */}
        <div className="space-y-1 mb-4">
          {navItems.map((item) => (
            <Button
              key={item.value}
              variant="ghost"
              onClick={() => onViewChange(item.value)}
              className={cn(
                "w-full justify-start gap-3 px-3 py-2.5 h-auto",
                activeView === item.value
                  ? "bg-neutral-800 text-white hover:bg-neutral-700"
                  : "text-neutral-400 hover:text-white hover:bg-neutral-900"
              )}
            >
              {item.icon}
              <span className="text-sm">{item.label}</span>
            </Button>
          ))}
        </div>

        {/* Collapsible Sections */}
        <div className="pt-3 border-t border-neutral-800">
          <CollapsibleSection title="Quick Actions">
            <Button
              variant="ghost"
              size="sm"
              className="w-full justify-start text-neutral-400 hover:text-white"
            >
              Create Project
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="w-full justify-start text-neutral-400 hover:text-white"
            >
              New Agent
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="w-full justify-start text-neutral-400 hover:text-white"
            >
              Import Data
            </Button>
          </CollapsibleSection>

          <CollapsibleSection title="Recent" defaultOpen>
            {conversations.length === 0 ? (
              <p className="text-xs text-neutral-500 px-3 py-1">No conversations yet</p>
            ) : (
              conversations.map((conv) => (
                <Button
                  key={conv.id}
                  variant="ghost"
                  size="sm"
                  onClick={() => handleConversationClick(conv.id)}
                  className={cn(
                    "w-full justify-start text-neutral-400 hover:text-white truncate",
                    activeConversationId === conv.id && "bg-neutral-800 text-white"
                  )}
                >
                  {conv.title}
                </Button>
              ))
            )}
          </CollapsibleSection>
        </div>
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-neutral-800">
        <Button
          variant="ghost"
          className="w-full justify-center text-neutral-400 hover:text-white text-sm"
        >
          Settings
        </Button>
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
              className="fixed inset-y-0 left-0 z-50 w-64 bg-neutral-950 border-r border-neutral-800 md:hidden"
            >
              {/* Mobile Header */}
              <div className="flex items-center justify-between p-4 border-b border-neutral-800">
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center text-primary-foreground text-sm font-bold">
                    S
                  </div>
                  <span className="text-white font-semibold">SwarmMind</span>
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => setIsOpen(false)}
                  className="text-neutral-400 hover:text-white"
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
      <div className="hidden md:flex flex-col fixed top-0 left-0 h-full w-64 bg-neutral-950 border-r border-neutral-800">
        {/* Desktop Header */}
        <div className="flex items-center justify-center p-4 border-b border-neutral-800">
          <span className="text-white font-semibold text-base">SwarmMind</span>
        </div>
        {sidebarContent}
      </div>

      {/* Mobile Header Bar */}
      <div className="md:hidden fixed top-0 left-0 right-0 z-30 bg-neutral-950 border-b border-neutral-800">
        <div className="flex items-center justify-between p-4">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center text-primary-foreground text-sm font-bold">
              S
            </div>
            <span className="text-white font-semibold">{pageTitle || "SwarmMind"}</span>
          </div>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setIsOpen(true)}
            className="text-neutral-400 hover:text-white"
          >
            <Menu />
          </Button>
        </div>
      </div>
    </>
  );
}
