export type DeerFlowInputFilePart = {
  file?: File
  filename?: string
  mediaType?: string
  type?: "file"
  url?: string
}

export interface DeerFlowPromptInputMessage {
  text: string
  files: DeerFlowInputFilePart[]
}
