/**
 * Auth-aware fetch wrapper.
 *
 * Reads the bearer token from localStorage and injects it into every request.
 * On 401, clears the stored token and dispatches an "auth:logout" event so the
 * AuthContext can redirect the user to the login page without circular imports.
 */

const TOKEN_KEY = "swm_token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

/**
 * Drop-in replacement for `fetch` that injects the auth header when a token
 * is stored. Handles 401 by clearing the token and emitting "auth:logout".
 */
export async function apiFetch(input: string | URL, init?: RequestInit): Promise<Response> {
  const token = getToken();
  const headers = new Headers(init?.headers);
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  const res = await fetch(input, { ...init, headers });
  if (res.status === 401) {
    clearToken();
    window.dispatchEvent(new Event("auth:logout"));
  }
  return res;
}

/**
 * Auth-aware JSON fetch. Throws on non-2xx responses.
 */
export async function apiFetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await apiFetch(path, init);
  if (!res.ok) {
    const detail = await res.text().catch(() => res.statusText);
    throw new Error(`HTTP ${res.status}: ${detail}`);
  }
  return res.json() as Promise<T>;
}
