"use client"

import { ExternalLinkIcon } from "lucide-react"
import type { ComponentProps } from "react"

import { Badge } from "@/components/ui/badge"
import {
  HoverCard,
  HoverCardContent,
  HoverCardTrigger,
} from "@/components/ui/hover-card"
import { cn } from "@/lib/utils"

export function CitationLink({
  href,
  children,
  className,
  ...props
}: ComponentProps<"a">) {
  const domain = extractDomain(href ?? "")
  const childrenText = typeof children === "string" ? children.replace(/^citation:\s*/i, "") : null
  const isGenericText = childrenText === "Source" || childrenText === "来源"
  const fallbackText = domain.length > 0 ? domain : "Source"
  const displayText = !isGenericText && childrenText ? childrenText : fallbackText

  const trigger = (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className={cn("inline-flex items-center align-baseline", className)}
      onClick={(event) => event.stopPropagation()}
      {...props}
    >
      <Badge
        variant="secondary"
        className="mx-0.5 h-5 cursor-pointer gap-1 rounded-full border border-[#e8e8e8] bg-white px-2 py-0.5 text-[11px] font-normal text-[#3f3f3f] shadow-[0_1px_2px_rgba(0,0,0,0.04)] hover:bg-[#f7f7f7]"
      >
        <span className="max-w-40 truncate">{displayText}</span>
        <ExternalLinkIcon className="size-3 text-[#7a7a7a]" />
      </Badge>
    </a>
  )

  return (
    <HoverCard>
      <HoverCardTrigger render={trigger} />
      <HoverCardContent className="w-80 rounded-lg border border-[#e8e8e8] bg-white p-0 shadow-[0_12px_35px_rgba(0,0,0,0.08)]">
        <div className="space-y-2 p-3">
          <div className="space-y-1">
            <h4 className="truncate text-sm font-medium leading-tight text-[#242424]">
              {displayText}
            </h4>
            {href && (
              <p className="truncate break-all text-xs text-[#737373]">
                {href}
              </p>
            )}
          </div>
          {href && (
            <a
              href={href}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-xs text-[#171717] underline decoration-[#d0d0d0] underline-offset-2 hover:decoration-[#171717]"
            >
              Visit source
              <ExternalLinkIcon className="size-3" />
            </a>
          )}
        </div>
      </HoverCardContent>
    </HoverCard>
  )
}

function extractDomain(url: string) {
  try {
    return new URL(url).hostname.replace(/^www\./i, "")
  } catch {
    return url
  }
}
