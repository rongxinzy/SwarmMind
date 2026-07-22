"use client"

import { Download } from "lucide-react"
import { Button } from "@/components/ui/button"

interface PresentationPreviewProps {
  blob: Blob
  title: string
}

export function PresentationPreview({ blob, title }: PresentationPreviewProps) {
  function handleDownload() {
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = title
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  return (
    <div className="flex h-full flex-col items-center justify-center bg-[#f7f7f7] p-6 text-center">
      <div className="max-w-sm rounded-lg border border-[#e4e4df] bg-white p-5 shadow-[0_1px_2px_rgba(0,0,0,0.03)]">
        <div className="text-sm font-medium text-[#242424]">{title}</div>
        <div className="mt-1 text-xs text-[#8a8a86]">PowerPoint presentation</div>
        <p className="mt-4 text-xs leading-5 text-[#6f6f69]">
          PPTX 文件暂不支持在线预览，请下载后查看。
        </p>
        <Button
          variant="outline"
          size="sm"
          className="mt-4 rounded-full"
          onClick={handleDownload}
        >
          <Download className="mr-1 size-4" />
          下载文件
        </Button>
      </div>
    </div>
  )
}
