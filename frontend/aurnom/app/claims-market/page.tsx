"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function ClaimsMarketLegacyPage() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/real-estate#claims-market");
  }, [router]);
  return (
    <main className="main-content">
      <p className="text-sm text-zinc-500 dark:text-cyan-500/80">Redirecting to Real Estate…</p>
    </main>
  );
}
