import test from "node:test"
import assert from "node:assert/strict"

import {
  artifactUrl,
  artifactDisplayPath,
  artifactMetadataForPath,
  artifactMetadataPath,
  buildArtifactMetadataIndex,
  isActiveContentArtifactPath,
  isSkillArtifactPath,
  createWriteFileArtifactReference,
  extractWriteFileArtifactContent,
  findLatestWriteFileArtifactReference,
  getWriteFileArtifactState,
  isVirtualArtifactPath,
  isWriteFileArtifactReference,
  mergeArtifactPaths,
  normalizeArtifactPath,
  parseWriteFileArtifactReference,
  resolveArtifactReference,
  skillArtifactPreviewPath,
} from "./artifacts.ts"

test("normalizes DeerFlow user-data artifact paths", () => {
  assert.equal(normalizeArtifactPath("mnt/user-data/reports/final.md"), "/mnt/user-data/reports/final.md")
  assert.equal(normalizeArtifactPath("/mnt/user-data/reports/final.md"), "/mnt/user-data/reports/final.md")
  assert.equal(normalizeArtifactPath("/mnt/user-data/reports/final%20report.md"), "/mnt/user-data/reports/final report.md")
  assert.equal(normalizeArtifactPath("/mnt/user-data/reports/final.md."), "/mnt/user-data/reports/final.md")
})

test("rejects non artifact paths", () => {
  assert.equal(normalizeArtifactPath(undefined), null)
  assert.equal(normalizeArtifactPath("https://example.com/report.md"), null)
  assert.equal(normalizeArtifactPath("/tmp/report.md"), null)
  assert.equal(isVirtualArtifactPath("/mnt/user-data/report.md"), true)
  assert.equal(isVirtualArtifactPath("/tmp/report.md"), false)
})

test("builds safe artifact URLs", () => {
  assert.equal(
    artifactUrl("thread 1", "/mnt/user-data/reports/final report.md", false),
    "/conversations/thread%201/artifacts/mnt/user-data/reports/final%20report.md",
  )
  assert.equal(
    artifactUrl("thread-1", "mnt/user-data/reports/final%20report.md", true),
    "/conversations/thread-1/artifacts/mnt/user-data/reports/final%20report.md?download=true",
  )
})

test("detects active web content artifacts", () => {
  assert.equal(isActiveContentArtifactPath("/mnt/user-data/outputs/page.html"), true)
  assert.equal(isActiveContentArtifactPath("/mnt/user-data/outputs/chart.svg"), true)
  assert.equal(isActiveContentArtifactPath("/mnt/user-data/outputs/data.csv"), false)
})

test("resolves DeerFlow skill package preview entry", () => {
  assert.equal(isSkillArtifactPath("/mnt/user-data/outputs/research.skill"), true)
  assert.equal(isSkillArtifactPath("/mnt/user-data/outputs/research.md"), false)
  assert.equal(
    skillArtifactPreviewPath("/mnt/user-data/outputs/research.skill"),
    "/mnt/user-data/outputs/research.skill/SKILL.md",
  )
  assert.equal(skillArtifactPreviewPath("/mnt/user-data/outputs/research.md"), null)
})

test("merges registered and inferred artifact paths", () => {
  assert.deepEqual(
    mergeArtifactPaths(
      ["/mnt/user-data/outputs/report.md", "mnt/user-data/outputs/report.md"],
      [undefined, "/tmp/ignore.txt", "/mnt/user-data/uploads/brief%201.txt"],
      ["/mnt/user-data/outputs/chart.svg."],
    ),
    [
      "/mnt/user-data/outputs/report.md",
      "/mnt/user-data/uploads/brief 1.txt",
      "/mnt/user-data/outputs/chart.svg",
    ],
  )
})

test("indexes registered artifact metadata by DeerFlow virtual path", () => {
  const artifacts = [
    {
      artifact_id: "artifact-1",
      path: "/mnt/user-data/outputs/report.md",
      name: "ignored.md",
      created_at: "2026-06-30T00:00:00Z",
    },
    {
      artifact_id: "artifact-2",
      name: "mnt/user-data/outputs/chart.svg",
      created_at: "2026-06-30T00:00:00Z",
    },
    {
      artifact_id: "artifact-3",
      storage_uri: "/tmp/not-user-data.txt",
      created_at: "2026-06-30T00:00:00Z",
    },
  ]

  const index = buildArtifactMetadataIndex(artifacts)

  assert.equal(artifactMetadataPath(artifacts[0]), "/mnt/user-data/outputs/report.md")
  assert.equal(artifactMetadataPath(artifacts[1]), "/mnt/user-data/outputs/chart.svg")
  assert.equal(artifactMetadataPath(artifacts[2]), null)
  assert.equal(index["/mnt/user-data/outputs/report.md"].artifact_id, "artifact-1")
  assert.equal(index["/mnt/user-data/outputs/chart.svg"].artifact_id, "artifact-2")
  assert.deepEqual(Object.keys(index), ["/mnt/user-data/outputs/report.md", "/mnt/user-data/outputs/chart.svg"])
})

test("looks up artifact metadata for direct and write-file references", () => {
  const index = buildArtifactMetadataIndex([
    {
      artifact_id: "artifact-1",
      path: "/mnt/user-data/outputs/report.md",
      size_bytes: 42,
      created_at: "2026-06-30T00:00:00Z",
    },
  ])
  const reference = createWriteFileArtifactReference({
    path: "/mnt/user-data/outputs/report.md",
    messageId: "message-1",
    toolCallId: "tool-1",
  })

  assert.equal(artifactMetadataForPath(index, "/mnt/user-data/outputs/report.md")?.artifact_id, "artifact-1")
  assert.equal(artifactMetadataForPath(index, reference)?.size_bytes, 42)
  assert.equal(artifactMetadataForPath(index, "/mnt/user-data/outputs/missing.md"), undefined)
})

test("resolves markdown references only for virtual artifacts", () => {
  assert.equal(
    resolveArtifactReference("thread-1", "/mnt/user-data/chart.svg"),
    "/conversations/thread-1/artifacts/mnt/user-data/chart.svg",
  )
  assert.equal(resolveArtifactReference("thread-1", "https://example.com"), "https://example.com")
  assert.equal(resolveArtifactReference(undefined, "/mnt/user-data/chart.svg"), "/mnt/user-data/chart.svg")
})

test("creates and parses DeerFlow write-file artifact references", () => {
  const reference = createWriteFileArtifactReference({
    path: "/mnt/user-data/outputs/final report.md",
    messageId: "message-1",
    toolCallId: "tool-1",
  })

  assert.equal(reference, "write-file:/mnt/user-data/outputs/final%20report.md?message_id=message-1&tool_call_id=tool-1")
  assert.equal(isWriteFileArtifactReference(reference), true)
  assert.deepEqual(parseWriteFileArtifactReference(reference), {
    path: "/mnt/user-data/outputs/final report.md",
    messageId: "message-1",
    toolCallId: "tool-1",
  })
  assert.equal(artifactDisplayPath(reference), "/mnt/user-data/outputs/final report.md")
  assert.equal(createWriteFileArtifactReference({ path: "/tmp/not-allowed.txt" }), null)
})

test("extracts write_file content from DeerFlow tool call references", () => {
  const reference = createWriteFileArtifactReference({
    path: "/mnt/user-data/outputs/report.md",
    messageId: "message-1",
    toolCallId: "tool-1",
  })
  const messages = [
    {
      id: "message-1",
      type: "ai",
      content: "",
      tool_calls: [
        {
          id: "tool-1",
          name: "write_file",
          args: {
            path: "/mnt/user-data/outputs/report.md",
            content: "# Report\n\nReady.",
          },
        },
      ],
    },
  ]

  assert.equal(extractWriteFileArtifactContent(messages, reference), "# Report\n\nReady.")
  assert.deepEqual(getWriteFileArtifactState(messages, reference), {
    content: "# Report\n\nReady.",
    status: "writing",
  })
  assert.equal(extractWriteFileArtifactContent(messages, "write-file:/mnt/user-data/outputs/report.md"), null)
})

test("rebuilds append-only write_file drafts from successful DeerFlow tool calls", () => {
  const reference = createWriteFileArtifactReference({
    path: "/mnt/user-data/outputs/report.md",
    messageId: "message-2",
    toolCallId: "tool-2",
  })
  const messages = [
    {
      id: "message-1",
      type: "ai",
      content: "",
      tool_calls: [{
        id: "tool-1",
        name: "write_file",
        args: { path: "/mnt/user-data/outputs/report.md", content: "# Report\n" },
      }],
    },
    { id: "result-1", type: "tool", tool_call_id: "tool-1", content: "OK" },
    {
      id: "message-2",
      type: "ai",
      content: "",
      tool_calls: [{
        id: "tool-2",
        name: "write_file",
        args: { path: "/mnt/user-data/outputs/report.md", content: "\nReady.", append: true },
      }],
    },
  ]

  assert.deepEqual(getWriteFileArtifactState(messages, reference), {
    content: "# Report\n\nReady.",
    status: "writing",
  })

  messages.push({ id: "result-2", type: "tool", tool_call_id: "tool-2", content: [{ type: "text", text: "OK" }] })
  assert.deepEqual(getWriteFileArtifactState(messages, reference), {
    content: "# Report\n\nReady.",
    status: "complete",
  })
})

test("does not preview a failed write_file draft", () => {
  const reference = createWriteFileArtifactReference({
    path: "/mnt/user-data/outputs/report.md",
    messageId: "message-1",
    toolCallId: "tool-1",
  })
  const messages = [
    {
      id: "message-1",
      type: "ai",
      content: "",
      tool_calls: [{
        id: "tool-1",
        name: "write_file",
        args: { path: "/mnt/user-data/outputs/report.md", content: "stale draft" },
      }],
    },
    { id: "result-1", type: "tool", tool_call_id: "tool-1", content: "Permission denied" },
  ]

  assert.deepEqual(getWriteFileArtifactState(messages, reference), {
    content: null,
    status: "failed",
  })
  assert.equal(extractWriteFileArtifactContent(messages, reference), null)
})

test("finds only the latest active write_file tool call for auto preview", () => {
  const messages = [
    {
      id: "message-1",
      type: "ai",
      content: "",
      tool_calls: [
        {
          id: "tool-1",
          name: "write_file",
          args: {
            path: "/mnt/user-data/outputs/old.md",
            content: "old",
          },
        },
      ],
    },
    {
      id: "message-2",
      type: "ai",
      content: "",
      tool_calls: [
        {
          id: "tool-2",
          name: "write_file",
          args: {
            path: "/mnt/user-data/outputs/new.md",
            content: "new",
          },
        },
      ],
    },
  ]

  assert.equal(
    findLatestWriteFileArtifactReference(messages),
    "write-file:/mnt/user-data/outputs/new.md?message_id=message-2&tool_call_id=tool-2",
  )
  assert.equal(
    findLatestWriteFileArtifactReference([
      ...messages,
      {
        id: "message-human",
        type: "human",
        content: "write a new report",
      },
    ]),
    null,
  )
  assert.equal(
    findLatestWriteFileArtifactReference([
      ...messages,
      {
        id: "message-3",
        type: "ai",
        content: "",
        tool_calls: [
          {
            id: "tool-3",
            name: "web_search",
            args: {
              query: "latest",
            },
          },
        ],
      },
    ]),
    null,
  )
})
