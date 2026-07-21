const ARTIFACT_CACHE_TTL_MS = 5 * 60 * 1000

interface CachedArtifactValue<T> {
  value: T
  expiresAt: number
}

const textCache = new Map<string, CachedArtifactValue<string>>()
const blobCache = new Map<string, CachedArtifactValue<Blob>>()
const textInFlight = new Map<string, Promise<string>>()
const blobInFlight = new Map<string, Promise<Blob>>()

export function cachedArtifactText(cacheKey: string) {
  return readCache(textCache, cacheKey)
}

export function cachedArtifactBlob(cacheKey: string) {
  return readCache(blobCache, cacheKey)
}

export function clearArtifactCache() {
  textCache.clear()
  blobCache.clear()
  textInFlight.clear()
  blobInFlight.clear()
}

export async function loadCachedArtifactText(cacheKey: string, load: () => Promise<string>) {
  const cached = cachedArtifactText(cacheKey)
  if (cached !== undefined) {
    return cached
  }

  const pending = textInFlight.get(cacheKey)
  if (pending) {
    return pending
  }

  const request = load()
    .then((value) => {
      writeCache(textCache, cacheKey, value)
      return value
    })
    .finally(() => {
      textInFlight.delete(cacheKey)
    })

  textInFlight.set(cacheKey, request)
  return request
}

export async function loadCachedArtifactBlob(cacheKey: string, load: () => Promise<Blob>) {
  const cached = cachedArtifactBlob(cacheKey)
  if (cached !== undefined) {
    return cached
  }

  const pending = blobInFlight.get(cacheKey)
  if (pending) {
    return pending
  }

  const request = load()
    .then((value) => {
      writeCache(blobCache, cacheKey, value)
      return value
    })
    .finally(() => {
      blobInFlight.delete(cacheKey)
    })

  blobInFlight.set(cacheKey, request)
  return request
}

function readCache<T>(cache: Map<string, CachedArtifactValue<T>>, cacheKey: string) {
  const cached = cache.get(cacheKey)
  if (!cached) {
    return undefined
  }
  if (cached.expiresAt <= Date.now()) {
    cache.delete(cacheKey)
    return undefined
  }
  return cached.value
}

function writeCache<T>(cache: Map<string, CachedArtifactValue<T>>, cacheKey: string, value: T) {
  cache.set(cacheKey, {
    value,
    expiresAt: Date.now() + ARTIFACT_CACHE_TTL_MS,
  })
}
