const TOKEN_KEY = "swm_token"

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY)
}

export async function apiFetch(input: string | URL, init?: RequestInit): Promise<Response> {
  const token = getToken()
  const headers = new Headers(init?.headers)
  if (token) {
    headers.set("Authorization", `Bearer ${token}`)
  }
  const res = await fetch(input, { ...init, headers })
  if (res.status === 401) {
    clearToken()
    window.dispatchEvent(new Event("auth:logout"))
  }
  return res
}

export async function apiFetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await apiFetch(path, init)
  if (!res.ok) {
    const detail = await res.text().catch(() => res.statusText)
    throw new Error(`HTTP ${res.status}: ${detail}`)
  }
  return res.json() as Promise<T>
}
