"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

type Stats = {
  brands: number;
  conversations: number;
  messages: number;
  orders: number;
  replies_by_status: Record<string, number>;
  llm_by_provider: Record<string, number>;
  avg_confidence: number;
};

export default function DashboardPage() {
  const { data, isLoading, error } = useQuery<Stats>({
    queryKey: ["stats"],
    queryFn: () => api("/api/admin/stats"),
  });

  if (isLoading) return <div className="text-[#8b94a7]">Loading…</div>;
  if (error) return <div className="text-[#f87171]">Error loading stats: {String(error)}</div>;

  const statuses = data?.replies_by_status ?? {};
  const providers = data?.llm_by_provider ?? {};
  const cards = [
    { label: "Brands", value: data?.brands ?? 0 },
    { label: "Conversations", value: data?.conversations ?? 0 },
    { label: "Messages", value: data?.messages ?? 0 },
    { label: "Orders", value: data?.orders ?? 0 },
    { label: "Pending Review", value: statuses["pending_review"] ?? 0 },
    { label: "Sent", value: statuses["sent"] ?? 0 },
  ];

  return (
    <main className="space-y-4">
      <div className="grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-6">
        {cards.map((c) => (
          <div key={c.label} className="card text-center">
            <div className="text-3xl font-semibold">{c.value}</div>
            <div className="mt-1 text-sm text-[#8b94a7]">{c.label}</div>
          </div>
        ))}
      </div>
      <div className="card col-span-full text-sm text-[#8b94a7]">
        Guardrails active: no-hallucination strict prompt · brand isolation enforced at retrieval · low-confidence
        replies routed to human review · all generations logged with provider + confidence telemetry.
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <div className="card">
          <h3 className="mb-2 font-medium">LLM provider usage</h3>
          {(Object.entries(providers).length === 0) ? (
            <p className="text-sm text-[#8b94a7]">No generations yet.</p>
          ) : (
            <ul className="text-sm">
              {Object.entries(providers).map(([k, v]) => (
                <li key={k} className="flex justify-between border-b border-[#1c222f] py-1">
                  <span>{k}</span> <span className="text-white">{v}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
        <div className="card">
          <h3 className="mb-2 font-medium">Avg reply confidence</h3>
          <div className="text-2xl">{((data?.avg_confidence ?? 0) * 100).toFixed(0)}%</div>
        </div>
      </div>
    </main>
  );
}