import { apiFetch } from "@/lib/api"

export async function fetchArtifactBlob(url: string) {
  const response = await apiFetch(url)
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`)
  }
  return response.blob()
}

export async function openArtifactBlobUrl(url: string) {
  const blob = await fetchArtifactBlob(url)
  const objectUrl = URL.createObjectURL(blob)
  const opened = window.open(objectUrl, "_blank", "noopener,noreferrer")
  if (!opened) {
    URL.revokeObjectURL(objectUrl)
    throw new Error("Unable to open artifact")
  }
  window.setTimeout(() => URL.revokeObjectURL(objectUrl), 60_000)
}

export async function downloadArtifactBlobUrl(url: string, filename: string) {
  const blob = await fetchArtifactBlob(url)
  const objectUrl = URL.createObjectURL(blob)
  const anchor = document.createElement("a")
  anchor.href = objectUrl
  anchor.download = filename
  anchor.rel = "noopener noreferrer"
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1_000)
}
