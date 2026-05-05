import * as React from "react"

import { cn } from "@/lib/utils"

const Textarea = React.forwardRef<HTMLTextAreaElement, React.ComponentProps<"textarea">>(
  function Textarea({ className, ...props }, ref) {
    return (
      <textarea
        data-slot="textarea"
        ref={ref}
        className={cn(
          "flex field-sizing-content min-h-24 w-full rounded-md border border-border bg-background px-3 py-2.5 text-[14px] leading-[22px] text-foreground transition-all outline-none placeholder:text-muted-foreground/70 focus-visible:border-ring focus-visible:ring-4 focus-visible:ring-ring/20 disabled:cursor-not-allowed disabled:bg-input/50 disabled:opacity-50 aria-invalid:border-destructive aria-invalid:ring-0 md:text-[14px] dark:bg-input/30 dark:disabled:bg-input/80 dark:aria-invalid:border-destructive/50",
          className
        )}
        {...props}
      />
    )
  }
)

export { Textarea }
