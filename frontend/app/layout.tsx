import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "@/components/providers";
import Nav from "@/components/nav";

export const metadata: Metadata = {
  title: "CX Assist — AI Reply Assistant",
  description: "Production-grade AI CX reply assistant with strict no-hallucination guardrails.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Providers>
          <div className="mx-auto max-w-6xl px-4 py-6">
            <Nav />
            {children}
          </div>
        </Providers>
      </body>
    </html>
  );
}