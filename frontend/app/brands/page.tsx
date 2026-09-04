"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { api, Brand } from "@/lib/api";

function BrandForm() {
  const { register, handleSubmit, reset } = useForm<{ name: string; description: string; website_url: string }>();
  const qc = useQueryClient();
  const create = useMutation({
    mutationFn: (b: unknown) => api<Brand>("/api/brands", { method: "POST", body: JSON.stringify(b) }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["brands"] });
      reset();
    },
  });

  return (
    <form
      onSubmit={handleSubmit((v) => create.mutate(v))}
      className="card grid gap-3 md:grid-cols-2"
    >
      <h2 className="md:col-span-2 text-sm font-semibold">Create Brand (manual CRUD — core)</h2>
      <input className="input" placeholder="Brand name *" {...register("name", { required: true })} />
      <input className="input" placeholder="Website URL" {...register("website_url")} />
      <input className="input md:col-span-2" placeholder="Description" {...register("description")} />
      <button className="btn md:col-span-2" type="submit" disabled={create.isPending}>
        {create.isPending ? "Creating…" : "Create Brand"}
      </button>
      {create.isError && <div className="md:col-span-2 text-sm text-[#f87171]">Error: {String(create.error)}</div>}
    </form>
  );
}

function BrandList() {
  const qc = useQueryClient();
  const { data: brands, isLoading } = useQuery<Brand[]>({ queryKey: ["brands"], queryFn: () => api("/api/brands") });
  const del = useMutation({
    mutationFn: (id: string) => api(`/api/brands/${id}`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["brands"] }),
  });

  if (isLoading) return <div className="text-[#8b94a7]">Loading…</div>;
  return (
    <div className="card">
      <h2 className="mb-3 text-sm font-semibold">Brands</h2>
      {!brands?.length && <div className="text-sm text-[#8b94a7]">No brands yet.</div>}
      <div className="grid gap-2">
        {brands?.map((b) => (
          <div key={b.id} className="flex items-center justify-between rounded-lg border border-[#232a3a] px-3 py-2 text-sm">
            <div>
              <span className="font-medium">{b.name}</span>
              {b.description && <span className="ml-2 text-[#8b94a7]">{b.description}</span>}
            </div>
            <button className="btn btn-danger" onClick={() => del.mutate(b.id)}>
              Delete
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function BrandsPage() {
  return (
    <main className="grid gap-4 md:grid-cols-2">
      <BrandForm />
      <BrandList />
    </main>
  );
}