export function extractTitleFromMarkdown(markdown: string) {
  const firstLine = markdown.trimStart().split("\n")[0]?.trim()
  if (!firstLine?.startsWith("# ")) {
    return undefined
  }

  const title = firstLine.slice(2).trim()
  if (!title || title.toLowerCase() === "untitled") {
    return undefined
  }
  return title
}
