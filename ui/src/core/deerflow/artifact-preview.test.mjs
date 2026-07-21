import test from "node:test"
import assert from "node:assert/strict"

import {
  appendHtmlPreviewBaseHref,
  appendHtmlPreviewSandboxCompatibility,
  appendHtmlPreviewScrollRestoration,
  createHtmlPreviewScrollKey,
  HTML_PREVIEW_SCROLL_MESSAGE_SOURCE,
} from "./artifact-preview.ts"

test("adds sandbox-safe temporary storage before artifact scripts", () => {
  const content = '<html><head><script src="app.js"></script></head><body></body></html>'
  const preview = appendHtmlPreviewSandboxCompatibility(content)

  assert.match(preview, /data-deerflow-artifact-sandbox-compatibility/)
  assert.match(preview, /install\("localStorage"\)/)
  assert.ok(preview.indexOf("data-deerflow-artifact-sandbox-compatibility") < preview.indexOf('src="app.js"'))
  assert.equal(appendHtmlPreviewSandboxCompatibility(preview), preview)
})

test("adds the artifact directory as the HTML preview base URL", () => {
  assert.equal(
    appendHtmlPreviewBaseHref(
      "<html><head><title>Report</title></head><body></body></html>",
      "/conversations/thread-1/artifacts/mnt/user-data/site/index.html",
      "http://localhost:3000/chat/thread-1",
    ),
    '<html><head><base href="http://localhost:3000/conversations/thread-1/artifacts/mnt/user-data/site/"><title>Report</title></head><body></body></html>',
  )
})

test("preserves an existing HTML base element", () => {
  const content = '<html><head><base href="https://example.com/"></head></html>'
  assert.equal(
    appendHtmlPreviewBaseHref(content, "/conversations/thread-1/artifacts/mnt/user-data/site/index.html"),
    content,
  )
})

test("injects keyed scroll restoration only once", () => {
  const content = "<html><body><main>Report</main></body></html>"
  const preview = appendHtmlPreviewScrollRestoration(content, "thread-1:/mnt/user-data/site/index.html")

  assert.match(preview, /data-deerflow-artifact-scroll-restoration/)
  assert.match(preview, new RegExp(HTML_PREVIEW_SCROLL_MESSAGE_SOURCE))
  assert.match(preview, new RegExp(createHtmlPreviewScrollKey("thread-1:/mnt/user-data/site/index.html")))
  assert.equal(appendHtmlPreviewScrollRestoration(preview, "another-key"), preview)
})
