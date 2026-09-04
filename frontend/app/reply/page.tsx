"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { useRouter } from "next/navigation";
import { api, Brand } from "@/lib/api";

type GenResp = {
  mode: "auto" | "human_review";
  conversation: { id: string };
  message: { id: string; draft_text: string; final_text: string; confidence: number; status: string; citation: string };
  validation: { ok: boolean; code: string; confidence: number; reason?: string };
};

export default function ReplyPage() {
  const router = useRouter();
  const { data: brands } = useQuery<Brand[]>({ queryKey: ["brands"], queryFn: () => api("/api/brands") });
  const { register, handleSubmit } = useForm<{ brand_id: string; customer_message: string }>();

  const gen = useMutation<GenResp, Error, { brand_id: string; customer_message: string }>({
    mutationFn: (p) => api("/api/conversations/generate", { method: "POST", body: JSON.stringify(p) }),
    onSuccess: () => router.refresh(),
  });

  const v = gen.data?.validation;

  return (
    <main className="grid gap-4 md:grid-cols-2">
      <form onSubmit={handleSubmit((p) => gen.mutate(p))} className="card grid gap-3 self-start">
        <h2 className="text-sm font-semibold">Generate AI Reply</h2>
        <select className="input" {...register("brand_id", { required: true })}>
          <option value="">Select brand…</option>
          {brands?.map((b) => (
            <option key={b.id} value={b.id}>{b.name}</option>
          ))}
        </select>
        <textarea className="input min-h-28" placeholder="Customer message…" {...register("customer_message", { required: true })} />
        <button className="btn" type="submit" disabled={gen.isPending}>
          {gen.isPending ? "Generating…" : "Generate"}
        </button>
        {gen.error && <div className="text-sm text-[#f87171]">{String(gen.error)}</div>}
      </form>

      <div className="card self-start">
        <h2 className="mb-3 text-sm font-semibold">Result</h2>
        {gen.data ? (
          <div className="space-y-3">
            <div>
              <span className={`badge ${v?.ok ? "bg-[#34d399]/15 text-[#34d399]" : "bg-[#f87171]/15 text-[#f87171]"}`}>
                {v?.ok ? "AUTO — approved & ready to send" : `HUMAN REVIEW — ${v?.reason ?? v?.code}`}
              </span>
            </div>
            <div className="rounded-lg border border-[#232a3a] p-3 text-sm leading-relaxed">{gen.data.message.draft_text}</div>
            {gen.data.message.citation && (
              <div className="text-xs text-[#22d3ee]">Citation: {gen.data.message.citation}</div>
            )}
            <div className="text-xs text-[#8b94a7]">
              Confidence: {(gen.data.message.confidence * 100).toFixed(1)}% · validation: {v?.code}
            </div>
            {!v?.ok && (
              <button className="btn btn-ghost" onClick={() => router.push("/review")}>
                Go to Review Queue
              </button>
            )}
          </div>
        ) : (
          <div className="text-sm text-[#8b94a7]">Select a brand, type a customer message, and generate.</div>
        )}
      </div>
    </main>
  );
}