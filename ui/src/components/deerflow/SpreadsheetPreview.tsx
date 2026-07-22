"use client"

import { useEffect, useState } from "react"
import ExcelJS from "exceljs"
import { Spinner } from "@/components/ui/spinner"
import {
  SPREADSHEET_PREVIEW_MAX_COLUMNS,
  SPREADSHEET_PREVIEW_MAX_ROWS,
  spreadsheetCellText,
  spreadsheetColumnLabel,
} from "@/core/deerflow/office-preview"

interface SpreadsheetPreviewProps {
  blob: Blob
  title: string
}

interface PreviewRow {
  cells: string[]
  key: string
}

interface PreviewSheet {
  name: string
  rows: PreviewRow[]
  truncatedRows: boolean
  truncatedColumns: boolean
  totalRows: number
  totalColumns: number
}

export function SpreadsheetPreview({ blob, title }: SpreadsheetPreviewProps) {
  const [sheet, setSheet] = useState<PreviewSheet | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    async function load() {
      setLoading(true)
      setError(null)

      try {
        const buffer = await blob.arrayBuffer()
        const workbook = new ExcelJS.Workbook()
        await workbook.xlsx.load(buffer)
        const worksheet = workbook.worksheets[0]

        if (!worksheet) {
          if (!cancelled) {
            setError("Spreadsheet is empty")
            setLoading(false)
          }
          return
        }

        const rawRows: string[][] = []
        let totalColumns = 0
        const worksheetRows = worksheet.getRows(1, SPREADSHEET_PREVIEW_MAX_ROWS + 1) ?? []
        for (const row of worksheetRows) {
          const cells: string[] = []
          let colIndex = 1
          for (const cell of row.values instanceof Array ? row.values.slice(1) : []) {
            if (colIndex > SPREADSHEET_PREVIEW_MAX_COLUMNS) break
            cells.push(spreadsheetCellText(cell))
            colIndex += 1
          }
          totalColumns = Math.max(totalColumns, cells.length)
          rawRows.push(cells)
        }

        // If getRows returned nothing, fall back to iterator
        if (rawRows.length === 0) {
          worksheet.eachRow({ includeEmpty: false }, (row) => {
            if (rawRows.length >= SPREADSHEET_PREVIEW_MAX_ROWS) return
            const cells: string[] = []
            let colIndex = 0
            for (const cell of row.values instanceof Array ? row.values.slice(1) : []) {
              if (colIndex >= SPREADSHEET_PREVIEW_MAX_COLUMNS) break
              cells.push(spreadsheetCellText(cell))
              colIndex += 1
            }
            totalColumns = Math.max(totalColumns, cells.length)
            rawRows.push(cells)
          })
        }

        const rows: PreviewRow[] = rawRows.map((cells, index) => ({
          key: `${index}`,
          cells,
        }))

        if (!cancelled) {
          setSheet({
            name: worksheet.name,
            rows,
            totalRows: rows.length,
            totalColumns,
            truncatedRows: rows.length >= SPREADSHEET_PREVIEW_MAX_ROWS,
            truncatedColumns: totalColumns >= SPREADSHEET_PREVIEW_MAX_COLUMNS,
          })
          setLoading(false)
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load spreadsheet")
          setLoading(false)
        }
      }
    }

    void load()

    return () => {
      cancelled = true
    }
  }, [blob])

  return (
    <div className="flex h-full min-h-0 flex-col bg-white">
      {loading && (
        <div className="flex flex-1 items-center justify-center">
          <Spinner className="text-muted-foreground" />
        </div>
      )}
      {error && !loading && (
        <div className="flex flex-1 flex-col items-center justify-center p-6 text-center text-sm text-muted-foreground">
          <p>Spreadsheet preview unavailable.</p>
          <p>{error}</p>
        </div>
      )}
      {!loading && sheet && (
        <>
          <div className="flex shrink-0 items-center justify-between gap-3 border-b border-[#eeeeec] bg-[#fbfbfa] px-3 py-2 pr-12">
            <div className="min-w-0 text-xs font-medium text-[#383836]">
              {sheet.name}
            </div>
            <div className="shrink-0 text-[11px] text-[#8a8a86]">
              {sheet.totalRows} rows · {sheet.totalColumns} columns
            </div>
          </div>
          <div className="min-h-0 flex-1 overflow-auto">
            {sheet.rows.length === 0 ? (
              <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
                Empty spreadsheet
              </div>
            ) : (
              <table className="min-w-full border-separate border-spacing-0 text-left text-xs">
                <thead>
                  <tr>
                    {Array.from({ length: Math.max(sheet.totalColumns, 1) }, (_, index) => (
                      <th
                        key={index}
                        className="sticky top-0 z-10 max-w-[180px] border-b border-r border-[#eeeeec] bg-[#f7f7f5] px-3 py-2 font-medium text-[#383836]"
                      >
                        <span className="block truncate">{spreadsheetColumnLabel(index + 1)}</span>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {sheet.rows.map((row) => (
                    <tr key={row.key} className="odd:bg-white even:bg-[#fcfcfb]">
                      {Array.from({ length: Math.max(sheet.totalColumns, 1) }, (_, colIndex) => (
                        <td
                          key={`${row.key}-${colIndex}`}
                          className="max-w-[180px] border-b border-r border-[#f1f1ef] px-3 py-2 text-[#4b4b48]"
                          title={row.cells[colIndex] ?? ""}
                        >
                          <span className="block truncate">{row.cells[colIndex] ?? ""}</span>
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
            {(sheet.truncatedRows || sheet.truncatedColumns) && (
              <div className="border-t border-[#eeeeec] bg-[#fbfbfa] px-3 py-2 text-[11px] text-[#8a8a86]">
                Preview limited to {SPREADSHEET_PREVIEW_MAX_ROWS} rows and {SPREADSHEET_PREVIEW_MAX_COLUMNS} columns.
              </div>
            )}
          </div>
        </>
      )}
      {!loading && !error && (
        <div className="pointer-events-none absolute left-3 top-3 z-20 max-w-[calc(100%-1.5rem)] rounded-md border border-[#e4e4df] bg-white/90 px-3 py-2 text-xs shadow-[0_1px_2px_rgba(0,0,0,0.05)] backdrop-blur">
          <div className="truncate font-medium text-[#2c2c2a]">{title}</div>
          <div className="mt-0.5 text-[#8a8a86]">Excel workbook</div>
        </div>
      )}
    </div>
  )
}
