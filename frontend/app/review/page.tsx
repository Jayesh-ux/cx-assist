"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ReplyLog } from "@/lib/api";

export default function ReviewPage() {
  const qc = useQueryClient();
  const { data, isLoading, refetch } = useQuery<ReplyLog[]>({ queryKey: ["review"], queryFn: () => api("/api/review") });
  const [editText, setEditText] = useState<Record<string, string>>({});

  const decide = useMutation({
    mutationFn: ({ id, action, final_text, note }: { id: string; action: string; final_text?: string; note?: string }) =>
      api(`/api/review/${id}/decide`, { method: "POST", body: JSON.stringify({ action, final_text, human_note: note }) }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["review"] });
      refetch();
    },
  });

  if (isLoading) return <div className="text-[#8b94a7]">Loading…</div>;
  const pending = (data ?? []).filter((r) => r.status !== "sent");

  return (
    <main className="card">
      <h2 className="mb-3 text-sm font-semibold">Review Queue ({pending.length})</h2>
      {pending.length === 0 && <div className="text-sm text-[#8b94a7]">Nothing to review.</div>}
      <div className="grid gap-4">
        {pending.map((r) => {
          const text = editText[r.id] ?? r.final_text ?? r.draft_text;
          return (
            <div key={r.id} className="rounded-lg border border-[#232a3a] p-3">
              <div className="mb-1 flex flex-wrap items-center gap-2 text-xs text-[#8b94a7]">
                <span className="text-[#e6e9f0]">{r.brand_name}</span>
                <span className={`badge bg-[#6366f1]/15 text-[#aaa9ff]`}>{r.status}</span>
                <span>confidence {(r.confidence * 100).toFixed(0)}%</span>
                <span>{r.validation_code}</span>
              </div>
              <div className="mb-2 rounded-lg bg-[#0b0e14] p-2 text-sm">{r.customer_message}</div>
              {r.citation && <div className="mb-2 text-xs text-[#22d3ee]">Citation: {r.citation}</div>}
              <textarea
                className="input min-h-24"
                value={text}
                onChange={(e) => setEditText((m) => ({ ...m, [r.id]: e.target.value }))}
              />
              <div className="mt-2 flex flex-wrap gap-2">
                <button className="btn" onClick={() => decide.mutate({ id: r.id, action: "approve" })}>Approve</button>
                <button className="btn btn-ghost" onClick={() => decide.mutate({ id: r.id, action: "edit", final_text: text })}>Save Edit</button>
                <button className="btn btn-ghost" onClick={() => decide.mutate({ id: r.id, action: "regenerate", final_text: text })}>Regenerate</button>
                <button className="btn btn-ghost" onClick={() => decide.mutate({ id: r.id, action: "manual", final_text: text })}>Manual</button>
                <button className="btn" style={{ background: "#34d399", color: "#0b0e14" }} onClick={() => decide.mutate({ id: r.id, action: "send", final_text: text })}>
                  Send
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </main>
  );
}