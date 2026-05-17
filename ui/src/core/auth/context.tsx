import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

import { apiFetch, apiFetchJson, clearToken, getToken, setToken } from "@/lib/api-client";

export interface AuthUser {
  user_id: string;
  email: string;
  display_name: string | null;
  role: string;
  status: string;
}

interface LoginResponse {
  token_id: string;
  token: string;
  user: AuthUser;
}

interface MeResponse {
  user: AuthUser;
  token_id: string;
  authenticated: boolean;
}

interface AuthState {
  user: AuthUser | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  hasUsers: boolean | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  setup: (email: string, password: string, displayName?: string) => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [hasUsers, setHasUsers] = useState<boolean | null>(null);

  // On mount: check if any users exist, then verify stored token
  useEffect(() => {
    async function init() {
      try {
        const statusRes = await fetch("/auth/status");
        if (statusRes.ok) {
          const { has_users } = (await statusRes.json()) as { has_users: boolean };
          setHasUsers(has_users);
          if (!has_users) {
            setIsLoading(false);
            return;
          }
        }
      } catch {
        // network error — assume users exist, let login handle it
        setHasUsers(true);
      }

      const token = getToken();
      if (!token) {
        setIsLoading(false);
        return;
      }

      try {
        const data = await apiFetchJson<MeResponse>("/auth/me");
        setUser(data.user);
      } catch {
        clearToken();
      } finally {
        setIsLoading(false);
      }
    }

    void init();
  }, []);

  // Handle 401s from any request (emitted by apiFetch)
  useEffect(() => {
    const handleAuthLogout = () => {
      setUser(null);
    };
    window.addEventListener("auth:logout", handleAuthLogout);
    return () => {
      window.removeEventListener("auth:logout", handleAuthLogout);
    };
  }, []);

  const login = async (email: string, password: string) => {
    const data = await apiFetchJson<LoginResponse>("/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    setToken(data.token);
    setUser(data.user);
    setHasUsers(true);
  };

  const logout = async () => {
    try {
      await apiFetch("/auth/logout", { method: "POST" });
    } finally {
      clearToken();
      setUser(null);
    }
  };

  const setup = async (email: string, password: string, displayName?: string) => {
    const data = await apiFetchJson<LoginResponse>("/auth/setup", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password, display_name: displayName ?? null }),
    });
    setToken(data.token);
    setUser(data.user);
    setHasUsers(true);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated: !!user,
        hasUsers,
        login,
        logout,
        setup,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
