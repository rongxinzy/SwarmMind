import { cn } from "@/lib/utils"

export function StreamingIndicator({
  className,
  size = "normal",
}: {
  className?: string
  size?: "normal" | "sm"
}) {
  const dotSize = size === "sm" ? "size-1.5 mx-0.5" : "size-2 mx-1"

  return (
    <div className={cn("flex items-center", className)} aria-label="SwarmMind is working">
      <span className={cn(dotSize, "animate-[deerflow-bounce_0.5s_infinite_alternate] rounded-full bg-muted-foreground opacity-100")} />
      <span
        className={cn(
          dotSize,
          "animate-[deerflow-bounce_0.5s_infinite_alternate] rounded-full bg-muted-foreground opacity-100 [animation-delay:0.2s]",
        )}
      />
      <span
        className={cn(
          dotSize,
          "animate-[deerflow-bounce_0.5s_infinite_alternate] rounded-full bg-muted-foreground opacity-100 [animation-delay:0.4s]",
        )}
      />
    </div>
  )
}
