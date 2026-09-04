"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  { href: "/", label: "Dashboard" },
  { href: "/brands", label: "Brands" },
  { href: "/reply", label: "Generate Reply" },
  { href: "/review", label: "Review Queue" },
  { href: "/ingest", label: "Knowledge Base" },
  { href: "/conversations", label: "Conversations" },
  { href: "/logs", label: "Logs" },
  { href: "/login", label: "Login" },
];

export default function Nav() {
  const pathname = usePathname() ?? "";
  return (
    <header className="mb-6 flex flex-wrap items-center justify-between gap-3">
      <div>
        <h1 className="text-xl font-semibold">CX Assist</h1>
        <p className="text-sm text-[#8b94a7]">AI CX reply assistant · strict no-hallucination guardrails</p>
      </div>
      <nav className="flex flex-wrap gap-2">
        {LINKS.map((l) => (
          <Link
            key={l.href}
            href={l.href}
            className={`rounded-lg px-3 py-1.5 text-sm transition ${
              pathname === l.href ? "bg-[#6366f1] text-white" : "text-[#8b94a7] hover:bg-[#12161f]"
            }`}
          >
            {l.label}
          </Link>
        ))}
      </nav>
    </header>
  );
}