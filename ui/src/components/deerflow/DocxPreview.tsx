"use client"

import { useEffect, useRef, useState } from "react"
import { renderAsync } from "docx-preview"
import { Spinner } from "@/components/ui/spinner"

interface DocxPreviewProps {
  blob: Blob
  title: string
}

export function DocxPreview({ blob, title }: DocxPreviewProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    const container = containerRef.current
    if (!container) return () => {}

    async function render(target: HTMLElement) {
      target.innerHTML = ""
      setLoading(true)
      setError(null)

      try {
        await renderAsync(blob, target, undefined, {
          className: "docx-preview",
          inWrapper: false,
        })
        if (!cancelled) {
          setLoading(false)
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to render docx")
          setLoading(false)
        }
      }
    }

    void render(container)

    return () => {
      cancelled = true
      container.innerHTML = ""
    }
  }, [blob])

  return (
    <div className="relative h-full w-full overflow-auto bg-[#f7f7f7]">
      {loading && (
        <div className="absolute inset-0 z-10 flex items-center justify-center bg-[#f7f7f7]/80">
          <Spinner className="text-muted-foreground" />
        </div>
      )}
      {error && (
        <div className="flex h-full flex-col items-center justify-center p-6 text-center text-sm text-muted-foreground">
          <p>Word preview unavailable.</p>
          <p>{error}</p>
        </div>
      )}
      <div ref={containerRef} className="min-h-full p-4" />
      <div className="pointer-events-none absolute left-3 top-3 z-20 max-w-[calc(100%-1.5rem)] rounded-md border border-[#e4e4df] bg-white/90 px-3 py-2 text-xs shadow-[0_1px_2px_rgba(0,0,0,0.05)] backdrop-blur">
        <div className="truncate font-medium text-[#2c2c2a]">{title}</div>
        <div className="mt-0.5 text-[#8a8a86]">Word document</div>
      </div>
    </div>
  )
}
