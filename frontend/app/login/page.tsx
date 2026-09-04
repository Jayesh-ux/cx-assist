"use client";

import { useState } from "react";
import type { FormEvent } from "react";
import { useRouter } from "next/navigation";
import { login } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setLoading(true); setError("");
    try {
      const user = await login(email, password);
      router.push(user.role === "admin" ? "/" : "/replying");
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="mx-auto mt-12 max-w-sm">
      <div className="card">
        <h1 className="mb-1 text-xl font-semibold">Sign in to CX Assist</h1>
        <p className="mb-4 text-sm text-[#8b94a7]">Tagged access for admins and support agents.</p>
        <form onSubmit={onSubmit} className="space-y-3">
          <input
            type="email" required placeholder="email@company.com"
            className="input" value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <input
            type="password" required placeholder="password"
            className="input" value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          {error && <p className="text-sm text-[#f87171]">{error}</p>}
          <button type="submit" disabled={loading} className="btn w-full">
            {loading ? "Signing in…" : "Sign in"}
          </button>
        </form>
      </div>
    </main>
  );
}