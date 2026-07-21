import test from "node:test"
import assert from "node:assert/strict"

import {
  spreadsheetCellText,
  spreadsheetColumnLabel,
} from "./office-preview.ts"

test("builds spreadsheet column labels", () => {
  assert.equal(spreadsheetColumnLabel(1), "A")
  assert.equal(spreadsheetColumnLabel(26), "Z")
  assert.equal(spreadsheetColumnLabel(27), "AA")
  assert.equal(spreadsheetColumnLabel(53), "BA")
  assert.equal(spreadsheetColumnLabel(0), "")
})

test("formats common ExcelJS cell values", () => {
  assert.equal(spreadsheetCellText(null), "")
  assert.equal(spreadsheetCellText(42), "42")
  assert.equal(spreadsheetCellText({ richText: [{ text: "Hello" }, { text: " world" }] }), "Hello world")
  assert.equal(spreadsheetCellText({ formula: "SUM(A1:A2)", result: 3 }), "3")
  assert.equal(spreadsheetCellText({ formula: "SUM(A1:A2)" }), "=SUM(A1:A2)")
  assert.equal(spreadsheetCellText({ text: "OpenAI", hyperlink: "https://openai.com" }), "OpenAI")
})
