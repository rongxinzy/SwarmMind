import type { Metadata } from "next"
import type { ReactNode } from "react"

import "../index.css"

export const metadata: Metadata = {
  title: "SwarmMind",
  description: "普通 B/S 架构的 Agent 聊天软件。",
}

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="zh-CN" suppressHydrationWarning>
      <body>{children}</body>
    </html>
  )
}
