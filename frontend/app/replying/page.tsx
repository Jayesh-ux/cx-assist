"use client";

import { useQuery } from "@tanstack/react-query";
import { api, getToken, getUser } from "@/lib/api";
import Link from "next/link";

export default function AgentDashboardPage() {
  const user = getUser();
  const { data } = useQuery<unknown[]>({
    queryKey: ["agentQueue"],
    queryFn: () => api("/api/review"),
    enabled: !!getToken(),
  });

  if (typeof window !== "undefined" && !getToken()) {
    return (
      <main className="card text-sm">
        Please <Link href="/login" className="text-[#6366f1]">sign in</Link> to view your queue.
      </main>
    );
  }

  const count = (data ?? []).filter((r: any) => (r as any).status !== "sent").length;
  return (
    <main className="grid gap-4 md:grid-cols-2">
      <div className="card">
        <h2 className="text-sm font-semibold">Welcome{user?.full_name ? `, ${user.full_name}` : ""}</h2>
        <p className="mt-1 text-sm text-[#8b94a7]">You are signed in as {user?.role ?? "agent"}.</p>
      </div>
      <div className="card">
        <h2 className="text-sm font-semibold">Your review queue</h2>
        <div className="mt-1 text-3xl font-semibold">{count}</div>
        <Link href="/review" className="btn btn-ghost mt-3">Open review queue</Link>
      </div>
    </main>
  );
}