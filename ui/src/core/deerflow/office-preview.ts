export const OFFICE_PREVIEW_MAX_BYTES = 30 * 1024 * 1024
export const SPREADSHEET_PREVIEW_MAX_ROWS = 200
export const SPREADSHEET_PREVIEW_MAX_COLUMNS = 40

export function spreadsheetColumnLabel(index: number) {
  if (!Number.isInteger(index) || index < 1) {
    return ""
  }

  let value = index
  let label = ""
  while (value > 0) {
    value -= 1
    label = String.fromCharCode(65 + (value % 26)) + label
    value = Math.floor(value / 26)
  }
  return label
}

export function spreadsheetCellText(value: unknown): string {
  if (value === null || value === undefined) {
    return ""
  }
  if (value instanceof Date) {
    return value.toISOString().replace("T", " ").replace(/\.000Z$/, " UTC")
  }
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    return String(value)
  }
  if (Array.isArray(value)) {
    return value.map(spreadsheetCellText).filter(Boolean).join(", ")
  }
  if (typeof value !== "object") {
    return String(value)
  }

  const record = value as Record<string, unknown>
  if (Array.isArray(record.richText)) {
    return record.richText
      .map((part) => typeof part === "object" && part !== null && "text" in part ? String(part.text ?? "") : "")
      .join("")
  }
  if ("result" in record && record.result !== undefined) {
    return spreadsheetCellText(record.result)
  }
  if ("text" in record) {
    return spreadsheetCellText(record.text)
  }
  if ("hyperlink" in record) {
    return spreadsheetCellText(record.hyperlink)
  }
  if ("error" in record) {
    return spreadsheetCellText(record.error)
  }
  if ("formula" in record) {
    return `=${spreadsheetCellText(record.formula)}`
  }

  return ""
}
