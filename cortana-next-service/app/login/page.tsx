"use client";

import { useState } from "react";
import { useAuth } from "@/hooks/useAuth";

export default function LoginPage() {
  const { login, error } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    const ok = await login(username.trim(), password);
    if (ok) {
      const next =
        typeof window !== "undefined"
          ? new URLSearchParams(window.location.search).get("next") || "/"
          : "/";
      window.location.href = next;
    }
  }

  return (
    <main className="min-h-screen flex items-center justify-center bg-[#FFFFFF]">
      <div className="w-full max-w-sm rounded-3xl border border-[#E5EEFF] bg-[#FFFFFF] p-10 shadow-lg text-[#0A0A0A]">
        <h1 className="text-3xl font-semibold text-[#0044CC] text-center mb-8">Welcome Back</h1>
        <form onSubmit={onSubmit} className="space-y-6">
          <div className="space-y-1">
            <label className="block text-sm font-medium text-[#003C99] tracking-wide">USERNAME</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full rounded-xl border border-[#BFD4FF] px-4 py-2.5 text-[#000000] placeholder-[#777] focus:outline-none focus:ring-2 focus:ring-[#004CFF] transition"
              placeholder=""
              autoFocus
            />
          </div>
          <div className="space-y-1">
            <label className="block text-sm font-medium text-[#003C99] tracking-wide">PASSWORD</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-xl border border-[#BFD4FF] px-4 py-2.5 text-[#000000] placeholder-[#777] focus:outline-none focus:ring-2 focus:ring-[#004CFF] transition"
              placeholder=""
            />
          </div>
          {error && <p className="text-sm text-red-600 text-center">{error}</p>}
          <button
            type="submit"
            className="w-full rounded-xl bg-[#004CFF] px-4 py-2.5 text-white font-semibold hover:bg-[#003C99] active:scale-[.98] transition"
          >
            Sign In
          </button>
        </form>
      </div>
    </main>
  );
}
