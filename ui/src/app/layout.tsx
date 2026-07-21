import type { Metadata } from "next"
import type { ReactNode } from "react"

import "../index.css"

export const metadata: Metadata = {
  title: "SwarmMind",
  description: "Team deliverable workbench.",
}

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="zh-CN" suppressHydrationWarning>
      <body>{children}</body>
    </html>
  )
}
