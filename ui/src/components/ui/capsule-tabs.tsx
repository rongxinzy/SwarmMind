"use client";

import * as React from "react";
import { motion } from "framer-motion";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { cn } from "@/lib/utils";

export interface CapsuleTabItem {
  value: string;
  label: string;
  content: React.ReactNode;
}

interface CapsuleTabsProps {
  items: CapsuleTabItem[];
  defaultValue?: string;
  className?: string;
  visibleCount?: number;
}

export default function CapsuleTabs({
  items,
  defaultValue,
  className,
  visibleCount = 5,
}: CapsuleTabsProps) {
  const [active, setActive] = React.useState(defaultValue || items[0].value);
  const [page, setPage] = React.useState(0);

  const totalPages = Math.ceil(items.length / visibleCount);

  const currentPageTabs = React.useMemo(() => {
    const start = page * visibleCount;
    return items.slice(start, start + visibleCount);
  }, [page, items, visibleCount]);

  const handlePrevPage = () => setPage((p) => Math.max(p - 1, 0));
  const handleNextPage = () => setPage((p) => Math.min(p + 1, totalPages - 1));

  const handleTabChange = (value: string) => {
    setActive(value);
    const tabIndex = items.findIndex((item) => item.value === value);
    if (tabIndex >= 0) {
      setPage(Math.floor(tabIndex / visibleCount));
    }
  };

  return (
    <div className={cn("flex flex-col items-center w-full", className)}>
      {totalPages > 1 && (
        <div className="flex gap-2 my-3">
          {Array.from({ length: totalPages }).map((_, idx) => (
            <button
              key={idx}
              onClick={() => setPage(idx)}
              className={cn(
                "w-4 h-4 border-2 transition-all cursor-pointer",
                idx === page ? "bg-primary border-primary" : "bg-muted border-border hover:border-foreground"
              )}
            />
          ))}
        </div>
      )}
      <div className="flex items-center gap-3 w-full max-w-lg">
        <Button
          variant="icon"
          onClick={handlePrevPage}
          disabled={page === 0}
          className="shrink-0"
        >
          <ChevronLeft className="w-5 h-5" />
        </Button>

        <Tabs value={active} onValueChange={handleTabChange} className="flex-1 flex flex-col">
          <TabsList className="flex gap-2 w-fit mx-auto justify-center bg-transparent p-0 border-0">
            {currentPageTabs.map((item) => {
              const isActive = item.value === active;
              return (
                <TabsTrigger
                  key={item.value}
                  value={item.value}
                  className={cn(
                    "px-5 py-2.5 whitespace-nowrap text-sm font-bold font-mono uppercase tracking-wider transition-all border-2",
                    isActive
                      ? "bg-primary text-primary-foreground border-primary shadow-brutal-sm"
                      : "bg-muted text-muted-foreground border-border hover:border-foreground hover:text-foreground"
                  )}
                >
                  <motion.span
                    className="contents"
                    whileHover={{ scale: 1.03 }}
                  >
                    {item.label}
                  </motion.span>
                </TabsTrigger>
              );
            })}
          </TabsList>

          {items.map((item) => (
            <TabsContent key={item.value} value={item.value}>
              <div className="bg-card border-2 border-border p-5">{item.content}</div>
            </TabsContent>
          ))}
        </Tabs>

        <Button
          variant="icon"
          onClick={handleNextPage}
          disabled={page === totalPages - 1}
          className="shrink-0"
        >
          <ChevronRight className="w-5 h-5" />
        </Button>
      </div>
    </div>
  );
}
