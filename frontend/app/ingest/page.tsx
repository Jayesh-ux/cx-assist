"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { api, Brand } from "@/lib/api";

export default function IngestPage() {
  const { data: brands } = useQuery<Brand[]>({ queryKey: ["brands"], queryFn: () => api("/api/brands") });
  const { register, handleSubmit, reset } = useForm<{ brand_id: string; policy_type: string; title: string; source_url: string; doc_text: string; crawl_url: string }>();

  const addDoc = useMutation({
    mutationFn: (p: { brand_id: string; policy_type: string; title: string; source_url: string; content: string }) =>
      api("/api/knowledge/documents", { method: "POST", body: JSON.stringify(p) }),
    onSuccess: () => reset(),
  });

  const crawl = useMutation({
    mutationFn: (p: { brand_id: string; url: string }) =>
      api("/api/knowledge/crawl", { method: "POST", body: JSON.stringify(p) }),
    onSuccess: () => reset(),
  });

  return (
    <main className="grid gap-4 md:grid-cols-2">
      <form
        onSubmit={handleSubmit((v) =>
          addDoc.mutate({
            brand_id: v.brand_id,
            policy_type: v.policy_type || "faq",
            title: v.title,
            source_url: v.source_url,
            content: v.doc_text,
          })
        )}
        className="card grid gap-3 self-start"
      >
        <h2 className="text-sm font-semibold">Add knowledge document (manual — core)</h2>
        <select className="input" {...register("brand_id", { required: true })}>
          <option value="">Select brand…</option>
          {brands?.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
        </select>
        <select className="input" {...register("policy_type")}>
          {["return", "refund", "shipping", "cancellation", "warranty", "exchange", "faq"].map((t) => (
            <option key={t} value={t}>{t}</option>
          ))}
        </select>
        <input className="input" placeholder="Title (e.g. Returns policy)" {...register("title")} />
        <input className="input" placeholder="Source URL" {...register("source_url")} />
        <textarea className="input min-h-32" placeholder="Policy text…" {...register("doc_text")} />
        <button className="btn" type="submit" disabled={addDoc.isPending}>
          {addDoc.isPending ? "Indexing…" : "Save & Index"}
        </button>
        {addDoc.isSuccess && <div className="text-sm text-[#34d399]">Document indexed.</div>}
      </form>

      <form
        onSubmit={handleSubmit((v) => crawl.mutate({ brand_id: v.brand_id, url: v.crawl_url }))}
        className="card grid gap-3 self-start"
      >
        <h2 className="text-sm font-semibold">Import from website (optional)</h2>
        <input className="input" placeholder="https://example.com/policies" {...register("crawl_url")} />
        <button className="btn btn-ghost" type="submit" disabled={crawl.isPending}>Start crawl</button>
        {crawl.isSuccess && <div className="text-sm text-[#34d399]">Crawl started in background.</div>}
      </form>
    </main>
  );
}