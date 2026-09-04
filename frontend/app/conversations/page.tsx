"use client";

import { useQuery } from "@tanstack/react-query";
import { api, ReplyLog } from "@/lib/api";

const STATUS_COLOR: Record<string, string> = {
  approved: "#34d399",
  edited: "#22d3ee",
  regenerated: "#22d3ee",
  manual: "#fbbf24",
  sent: "#9ca3af",
  pending_review: "#f87171",
};

export default function ConversationsPage() {
  const { data, isLoading } = useQuery<ReplyLog[]>({ queryKey: ["replies"], queryFn: () => api("/api/replies") });

  if (isLoading) return <div className="text-[#8b94a7]">Loading…</div>;

  return (
    <main className="card">
      <h2 className="mb-3 text-sm font-semibold">Reply Log ({data?.length ?? 0})</h2>
      {!data?.length && <div className="text-sm text-[#8b94a7]">No replies yet.</div>}
      <div className="grid gap-3">
        {data?.map((r) => (
          <div key={r.id} className="rounded-lg border border-[#232a3a] p-3 text-sm">
            <div className="mb-1 flex flex-wrap items-center gap-2 text-xs text-[#8b94a7]">
              <span className="text-[#e6e9f0]">{r.brand_name}</span>
              <span className="badge" style={{ background: `${STATUS_COLOR[r.status] ?? "#6366f1"}22`, color: STATUS_COLOR[r.status] ?? "#6366f1" }}>
                {r.status}
              </span>
              <span>{(r.confidence * 100).toFixed(0)}% · {String(r.created_at ?? "").slice(0, 19).replace("T", " ")}</span>
            </div>
            <div className="mb-1 text-[#8b94a7]">Customer: {r.customer_message}</div>
            <div className="rounded bg-[#0b0e14] p-2">{r.final_text || r.draft_text}</div>
          </div>
        ))}
      </div>
    </main>
  );
}