"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

type AILog = {
  provider: string;
  model_used: string;
  customer_message: string;
  llm_response: string;
  confidence: number;
  latency_ms: number;
  status: string;
  created_at: string;
};

type Audit = {
  action: string;
  entity_type: string;
  entity_id: string;
  actor_user_id: string;
  created_at: string;
};

export default function LogsPage() {
  const { data: logs } = useQuery<AILog[]>({ queryKey: ["ailogs"], queryFn: () => api("/api/admin/logs") });
  const { data: audits } = useQuery<Audit[]>({ queryKey: ["audit"], queryFn: () => api("/api/admin/audit") });

  return (
    <main className="grid gap-4 md:grid-cols-2">
      <div className="card">
        <h2 className="mb-2 text-sm font-semibold">AI generation logs ({logs?.length ?? 0})</h2>
        {(logs ?? []).slice(0, 25).map((l) => (
          <div key={l.created_at} className="rounded-lg border border-[#232a3a] p-2 my-2 text-xs">
            <span className="text-[#22d3ee]">{l.provider || "-"}</span> · {(l.confidence ?? 0) * 100}% · {l.latency_ms}ms
            <div className="text-[#8b94a7]">{(l.customer_message || "").slice(0, 80)}</div>
          </div>
        ))}
      </div>
      <div className="card">
        <h2 className="mb-2 text-sm font-semibold">Audit trail ({audits?.length ?? 0})</h2>
        {(audits ?? []).slice(0, 25).map((a) => (
          <div key={a.created_at} className="rounded-lg border border-[#232a3a] p-2 my-2 text-xs">
            <span className="text-[#fbbf24]">{a.action}</span> @ {a.entity_type}
            <div className="text-[#8b94a7]">by {a.actor_user_id || "system"} · {String(a.created_at).slice(0, 19).replace("T", " ")}</div>
          </div>
        ))}
        {(audits ?? []).length === 0 && <p className="text-sm text-[#8b94a7]">No audit events yet.</p>}
      </div>
    </main>
  );
}