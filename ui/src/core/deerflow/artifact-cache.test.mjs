import test from "node:test"
import assert from "node:assert/strict"

import {
  clearArtifactCache,
  loadCachedArtifactBlob,
  loadCachedArtifactText,
} from "./artifact-cache.ts"

test("caches text artifact content by key", async () => {
  clearArtifactCache()
  let calls = 0
  const load = async () => {
    calls += 1
    return calls === 1 ? "first" : "second"
  }

  try {
    assert.equal(await loadCachedArtifactText("text-key", load), "first")
    assert.equal(await loadCachedArtifactText("text-key", load), "first")
    assert.equal(calls, 1)
  } finally {
    clearArtifactCache()
  }
})

test("deduplicates concurrent blob artifact loads", async () => {
  clearArtifactCache()
  let calls = 0
  const load = async () => {
    calls += 1
    return new Blob([`blob-${calls}`])
  }

  try {
    const [first, second] = await Promise.all([
      loadCachedArtifactBlob("blob-key", load),
      loadCachedArtifactBlob("blob-key", load),
    ])
    assert.equal(await first.text(), "blob-1")
    assert.equal(await second.text(), "blob-1")
    assert.equal(calls, 1)
  } finally {
    clearArtifactCache()
  }
})
