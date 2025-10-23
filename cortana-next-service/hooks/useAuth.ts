"use client";
import { useCallback, useEffect, useState } from "react";
import { checkCredentials, setSessionClient, clearSessionClient, isAuthenticated } from "@/lib/auth";

export function useAuth() {
  const [authed, setAuthed] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => { setAuthed(isAuthenticated()); setLoading(false); }, []);

  const login = useCallback(async (username: string, password: string) => {
    setError(null);
    if (!checkCredentials(username, password)) { setError("Invalid credentials"); return false; }
    const r = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",               // <- ensure browser applies the Set-Cookie
      body: JSON.stringify({ username, password }),
    });
    if (!r.ok) { setError("Login failed"); return false; }
    setSessionClient();                     // <- also set cookie client-side
    setAuthed(true);
    return true;
  }, []);

  const logout = useCallback(async () => {
    await fetch("/api/auth/logout", { method: "POST", credentials: "include" });
    clearSessionClient();
    setAuthed(false);
  }, []);

  return { authed, loading, error, login, logout };
}
