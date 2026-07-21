"use client"

import { useMemo } from "react"
import type { AnchorHTMLAttributes, ImgHTMLAttributes } from "react"

import {
  MessageResponse,
  type MessageResponseProps,
} from "@/components/ai-elements/message"
import {
  normalizeArtifactPath,
  resolveArtifactReference,
} from "@/core/deerflow/artifacts"
import { cn } from "@/lib/utils"

import { CitationLink } from "./CitationLink"

function isExternalUrl(href: string | undefined) {
  return Boolean(href && /^https?:\/\//.test(href))
}

export type MarkdownContentProps = {
  content: string
  isLoading: boolean
  className?: string
  conversationId?: string
  remarkPlugins?: MessageResponseProps["remarkPlugins"]
  rehypePlugins?: MessageResponseProps["rehypePlugins"]
  components?: MessageResponseProps["components"]
  onArtifactSelect?: (file: string) => void
}

export function MarkdownContent({
  content,
  isLoading,
  className,
  conversationId,
  components: componentsFromProps,
  onArtifactSelect,
  ...props
}: MarkdownContentProps) {
  const components = useMemo(
    () => ({
      a: (anchorProps: AnchorHTMLAttributes<HTMLAnchorElement>) => {
        if (typeof anchorProps.children === "string") {
          const citationMatch = /^citation:(.+)$/.exec(anchorProps.children)
          if (citationMatch) {
            const [, text] = citationMatch
            return <CitationLink {...anchorProps}>{text}</CitationLink>
          }
        }
        const resolvedHref = anchorProps.href
          ? resolveArtifactReference(conversationId, anchorProps.href)
          : undefined
        const artifactPath = normalizeArtifactPath(anchorProps.href)
        const external = isExternalUrl(resolvedHref)
        const { className: anchorClassName, target, rel, onClick, ...rest } = anchorProps
        return (
          <a
            {...rest}
            href={resolvedHref}
            className={cn(
              "text-primary decoration-primary/30 underline underline-offset-2 transition-colors hover:decoration-primary/60",
              anchorClassName,
            )}
            target={target ?? (external ? "_blank" : undefined)}
            rel={rel ?? (external ? "noopener noreferrer" : undefined)}
            onClick={(event) => {
              onClick?.(event)
              if (!event.defaultPrevented && artifactPath && onArtifactSelect) {
                event.preventDefault()
                onArtifactSelect(artifactPath)
              }
            }}
          />
        )
      },
      img: ({ className: imageClassName, src, alt, ...imageProps }: ImgHTMLAttributes<HTMLImageElement>) => {
        if (typeof src !== "string" || !src) {
          return null
        }
        const resolvedSrc = resolveArtifactReference(conversationId, src)
        const artifactPath = normalizeArtifactPath(src)
        return (
          <a
            href={resolvedSrc}
            target="_blank"
            rel="noopener noreferrer"
            onClick={(event) => {
              if (artifactPath && onArtifactSelect) {
                event.preventDefault()
                onArtifactSelect(artifactPath)
              }
            }}
          >
            <img
              {...imageProps}
              className={cn("max-w-[90%] overflow-hidden rounded-lg", imageClassName)}
              src={resolvedSrc}
              alt={alt ?? "image"}
            />
          </a>
        )
      },
      ...componentsFromProps,
    }),
    [componentsFromProps, conversationId, onArtifactSelect],
  )

  if (!content) {
    return null
  }

  return (
    <MessageResponse
      className={className}
      components={components}
      isAnimating={isLoading}
      {...props}
    >
      {content}
    </MessageResponse>
  )
}
