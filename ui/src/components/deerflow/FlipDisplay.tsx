"use client"

import { AnimatePresence, motion } from "motion/react"
import type { ReactNode } from "react"

import { cn } from "@/lib/utils"

export function FlipDisplay({
  children,
  className,
  uniqueKey,
}: {
  children: ReactNode
  className?: string
  uniqueKey: string
}) {
  return (
    <div className={cn("relative overflow-hidden", className)}>
      <AnimatePresence mode="wait">
        <motion.div
          key={uniqueKey}
          initial={{ y: 8, opacity: 0 }}
          animate={{ y: 2, opacity: 1 }}
          exit={{ y: -8, opacity: 0 }}
          transition={{ duration: 0.25, ease: [0.4, 0, 0.2, 1] }}
        >
          {children}
        </motion.div>
      </AnimatePresence>
    </div>
  )
}
